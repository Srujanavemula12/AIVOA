"""
LangGraph AI Agent for the HCP Interaction module.

Role of the agent
------------------
The agent sits behind the conversational side of the "Log Interaction" screen.
A field rep can type/speak naturally ("Just met Dr. Rao, discussed Cardivex,
she wants samples next week, seemed positive") and the agent:

  1. Figures out which tool(s) the request needs (log vs edit vs lookup vs
     follow-up) using the LLM's tool-calling ability.
  2. Uses the LLM to summarize the free text and pull out structured fields
     (topics/drugs discussed, sentiment, action items) before those tools run.
  3. Executes the DB-backed tool(s) via a LangGraph ToolNode.
  4. Returns a natural-language confirmation back to the rep, plus the
     structured record that now also shows up in the form view - so the
     structured form and the chat interface stay in sync (same underlying
     Interaction rows).

Five tools (spec requires >= 5, log + edit are mandatory):
  1. log_interaction      (mandatory)
  2. edit_interaction     (mandatory)
  3. extract_entities     - LLM-only NLP pass over freeform text
  4. schedule_followup    - creates a follow-up task tied to an interaction
  5. get_hcp_history      - retrieves past interactions for context/continuity
"""
import os
import json
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from sqlalchemy.orm import Session

from . import models

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
# gemma2-9b-it was decommissioned by Groq (see README) - default switched to
# llama-3.3-70b-versatile, which also handles multi-step tool reasoning better.
GROQ_MODEL_FALLBACK = os.getenv("GROQ_MODEL_FALLBACK", "llama-3.3-70b-versatile")

llm = ChatGroq(model=GROQ_MODEL, temperature=0, api_key=os.getenv("GROQ_API_KEY"))

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
# The tools need DB access, but LangChain @tool functions are plain callables.
# We use a module-level "current session" pattern set per-request by the
# FastAPI route (see main.py) - simple and sufficient for a demo/assignment
# scope. In a production system you'd inject this via a proper context.
_db_session: Session | None = None


def set_session(db: Session):
    global _db_session
    _db_session = db


@tool
def log_interaction(hcp_id: str, raw_notes: str, interaction_type: str = "visit", hcp_name: str = "") -> str:
    """Log a new interaction with an HCP. Summarizes the notes and extracts
    topics/sentiment/materials/samples/outcomes using the LLM, then saves a
    new Interaction record. Use this when the rep describes a NEW visit/call/
    email that hasn't been logged yet. hcp_name is the doctor's name if the
    rep mentioned it (e.g. 'Dr. Rao') - pass it along so the form can display it."""
    extraction = _run_extraction(raw_notes)

    interaction = models.Interaction(
        hcp_id=hcp_id,
        interaction_type=interaction_type,
        channel="chat",
        raw_notes=raw_notes,
        summary=extraction["summary"],
        topics_discussed=extraction["topics"],
        sentiment=extraction["sentiment"],
        entities=extraction,
        hcp_name=hcp_name or extraction.get("hcp_name"),
        attendees=extraction.get("attendees") or [],
        materials_shared=extraction.get("materials_shared") or [],
        samples_distributed=extraction.get("samples_distributed") or [],
        outcomes=extraction.get("outcomes"),
        follow_up_actions=extraction.get("follow_up_actions"),
        suggested_followups=extraction.get("action_items") or [],
    )
    _db_session.add(interaction)
    _db_session.commit()
    _db_session.refresh(interaction)

    return json.dumps({
        "status": "logged",
        "interaction_id": interaction.id,
        "summary": interaction.summary,
        "topics": interaction.topics_discussed,
        "sentiment": interaction.sentiment,
        "materials_shared": interaction.materials_shared,
        "samples_distributed": interaction.samples_distributed,
        "suggested_followups": interaction.suggested_followups,
    })


@tool
def edit_interaction(interaction_id: str, updated_notes: str) -> str:
    """Edit/amend a previously logged interaction. Re-runs summarization and
    entity extraction on the updated notes and overwrites the stored fields.
    Use this when the rep says something like 'actually, add/change ...' about
    an interaction that was already logged."""
    interaction = _db_session.get(models.Interaction, interaction_id)
    if not interaction:
        return json.dumps({"status": "error", "message": f"No interaction found with id {interaction_id}"})

    extraction = _run_extraction(updated_notes)

    interaction.raw_notes = updated_notes
    interaction.summary = extraction["summary"]
    interaction.topics_discussed = extraction["topics"]
    interaction.sentiment = extraction["sentiment"]
    interaction.entities = extraction
    if extraction.get("materials_shared"):
        interaction.materials_shared = extraction["materials_shared"]
    if extraction.get("samples_distributed"):
        interaction.samples_distributed = extraction["samples_distributed"]
    if extraction.get("outcomes"):
        interaction.outcomes = extraction["outcomes"]
    _db_session.commit()
    _db_session.refresh(interaction)

    return json.dumps({
        "status": "updated",
        "interaction_id": interaction.id,
        "summary": interaction.summary,
    })


@tool
def extract_entities(text: str) -> str:
    """Run pure NLP extraction over freeform text and return topics/drugs
    discussed, sentiment, and a short summary - without saving anything.
    Useful when the rep just wants a quick structured preview before
    deciding to log it."""
    return json.dumps(_run_extraction(text))


@tool
def schedule_followup(interaction_id: str, description: str, due_date: str = "") -> str:
    """Create a follow-up task linked to an interaction, e.g. 'send samples
    next week' or 'schedule a lunch-and-learn'. due_date is an optional
    ISO date string (YYYY-MM-DD)."""
    interaction = _db_session.get(models.Interaction, interaction_id)
    if not interaction:
        return json.dumps({"status": "error", "message": f"No interaction found with id {interaction_id}"})

    followup = models.FollowUp(
        interaction_id=interaction_id,
        description=description,
        due_date=due_date or None,
    )
    _db_session.add(followup)
    _db_session.commit()
    _db_session.refresh(followup)

    return json.dumps({"status": "scheduled", "followup_id": followup.id, "description": description})


@tool
def get_hcp_history(hcp_id: str, limit: str = "5") -> str:
    """Retrieve the most recent past interactions for an HCP, so the agent
    (or the rep) has context before logging a new one, e.g. to avoid
    duplicate follow-ups or to reference the last conversation."""
    limit = int(limit) if str(limit).isdigit() else 5
    rows = (
        _db_session.query(models.Interaction)
        .filter(models.Interaction.hcp_id == hcp_id)
        .order_by(models.Interaction.created_at.desc())
        .limit(limit)
        .all()
    )
    history = [
        {
            "id": r.id,
            "date": r.created_at.isoformat(),
            "type": r.interaction_type,
            "summary": r.summary,
            "sentiment": r.sentiment,
        }
        for r in rows
    ]
    return json.dumps(history)


TOOLS = [log_interaction, edit_interaction, extract_entities, schedule_followup, get_hcp_history]
llm_with_tools = llm.bind_tools(TOOLS)


def _run_extraction(text: str) -> dict:
    """Shared LLM helper: summarize + extract structured fields from raw notes.
    Falls back to a plain heuristic if the LLM call fails (keeps the demo
    resilient if the API key/quota isn't available while recording)."""
    prompt = (
        "You are a life-sciences CRM assistant. Given a field rep's notes about "
        "a conversation with a healthcare professional (HCP), return ONLY a JSON "
        "object with keys: "
        "summary (1-2 sentences), "
        "topics (list of drug/product or subject names mentioned), "
        "sentiment (one of positive/neutral/negative), "
        "hcp_name (the HCP's name if mentioned, e.g. 'Dr. Rao', else empty string), "
        "attendees (list of any other people mentioned as present, else []), "
        "materials_shared (list of marketing materials mentioned, e.g. 'Brochure', else []), "
        "samples_distributed (list of drug samples mentioned as given, else []), "
        "outcomes (1 short sentence on the agreed outcome, if any, else empty string), "
        "follow_up_actions (1 short sentence describing what the rep said they'd do next, else empty string), "
        "action_items (list of short, separately-actionable follow-up tasks implied, if any, else []).\n\n"
        f"Notes: {text}"
    )
    try:
        resp = llm.invoke(prompt)
        content = resp.content.strip()
        if content.startswith("```"):
            content = content.strip("`").lstrip("json").strip()
        data = json.loads(content)
        return {
            "summary": data.get("summary", text[:200]),
            "topics": data.get("topics", []),
            "sentiment": data.get("sentiment", "neutral"),
            "hcp_name": data.get("hcp_name", ""),
            "attendees": data.get("attendees", []),
            "materials_shared": data.get("materials_shared", []),
            "samples_distributed": data.get("samples_distributed", []),
            "outcomes": data.get("outcomes", ""),
            "follow_up_actions": data.get("follow_up_actions", ""),
            "action_items": data.get("action_items", []),
        }
    except Exception:
        return {
            "summary": text[:200], "topics": [], "sentiment": "neutral",
            "hcp_name": "", "attendees": [], "materials_shared": [],
            "samples_distributed": [], "outcomes": "", "follow_up_actions": "",
            "action_items": [],
        }


# ---------------------------------------------------------------------------
# LangGraph wiring
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


SYSTEM_PROMPT = SystemMessage(content=(
    "You are the AIVOA CRM assistant for pharma field reps logging interactions "
    "with healthcare professionals (HCPs). Decide which tool(s) to call based on "
    "what the rep says: log_interaction for a brand-new visit/call, "
    "edit_interaction to change one already logged, extract_entities for a "
    "quick preview, schedule_followup for action items, and get_hcp_history for "
    "context. "
    "IMPORTANT: never call schedule_followup in the same turn as log_interaction. "
    "If a new interaction needs both a log and a follow-up, call ONLY "
    "log_interaction first. Wait for its result (the real interaction_id) to "
    "come back, then in your next response call schedule_followup using that "
    "exact id. Never guess or invent an interaction_id. "
    "If the rep's notes clearly state a concrete next action (e.g. 'wants "
    "samples next week'), go ahead and schedule it yourself on that next turn. "
    "If it's not clear whether they want a follow-up scheduled, ask them first "
    "instead of guessing. "
    "Always confirm what you did in one short, friendly sentence after "
    "the tool result comes back."
))


def call_model(state: AgentState):
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState):
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END


graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(TOOLS))
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

agent_app = graph.compile()


def run_agent(db: Session, user_message: str) -> dict:
    """Entry point used by the FastAPI route."""
    set_session(db)
    result = agent_app.invoke({"messages": [("user", user_message)]})
    final_message = result["messages"][-1]

    tool_names = [
        m.name for m in result["messages"]
        if getattr(m, "type", None) == "tool"
    ]

    return {"reply": final_message.content, "tool_calls": tool_names}
