# AIVOA CRM — HCP Interaction Module (Log Interaction Screen)

Assignment submission for the Full Stack Developer – AI Applications role.

> **Note on the LLM model:** the spec originally referenced Groq's
> `gemma2-9b-it`, which Groq has since decommissioned. The default model was
> switched to `llama-3.3-70b-versatile`, configurable via the `GROQ_MODEL`
> env var in `backend/.env`. Also fixed a sequencing bug where the agent
> could call `schedule_followup` before `log_interaction`'s result (and
> therefore the real `interaction_id`) came back — the system prompt now
> requires `log_interaction` to complete first when both are needed in the
> same request.

A prototype of the "Log Interaction" screen for an AI-first CRM built for
pharma field reps. Reps can log a conversation with a Healthcare Professional
(HCP) two ways: a **structured form**, or a **conversational chat interface**
backed by a **LangGraph agent** running on **Groq**.

---

## Architecture

```
frontend/   React + Redux Toolkit UI (Log Interaction screen)
backend/    FastAPI + SQLAlchemy + LangGraph agent
```

Both entry paths (form and chat) write to the same `Interaction` table, so
whatever you log in chat instantly shows up in the interaction list, and
vice versa.

### The LangGraph Agent

The agent (`backend/app/agent.py`) sits behind `/agent/chat`. It receives the
rep's freeform message, decides which tool(s) to call based on intent, runs
them against the database, and replies in natural language. It's built as a
small `StateGraph`: an `agent` node (Groq LLM with tools bound) and a `tools`
node (LangGraph's `ToolNode`), looping until the model stops requesting tool
calls.

**Why an agent and not just a form-filler:** reps talk the way people talk —
"met Dr. Rao, she wants samples next week" mixes a log, a sentiment, and a
follow-up in one sentence. The agent's job is to parse that into the right
structured actions instead of forcing the rep to fill out three fields by hand.

#### The 5 tools

| Tool | Purpose |
|---|---|
| **`log_interaction`** *(mandatory)* | Creates a new `Interaction` row. Runs the raw notes through the LLM to produce a summary, extracted topics/drug names, and sentiment before saving. |
| **`edit_interaction`** *(mandatory)* | Looks up an existing interaction by id and overwrites it with freshly re-extracted fields from updated notes — used when a rep corrects or adds detail after the fact. |
| **`extract_entities`** | Runs the same LLM extraction (summary/topics/sentiment/action items) without saving — a "preview" tool, or usable standalone for quick NLP on any text. |
| **`schedule_followup`** | Creates a `FollowUp` row tied to an interaction (e.g. "send samples next week"), so action items don't get lost in the notes. |
| **`get_hcp_history`** | Pulls the N most recent interactions for an HCP, giving the agent (or the rep) context before logging something new — e.g. to avoid duplicate follow-ups. |

`log_interaction` and `edit_interaction` both call a shared `_run_extraction`
helper, which is the actual LLM call (`gemma2-9b-it` on Groq) that does
summarization + entity/sentiment extraction. If the Groq call fails (e.g. no
API key set), extraction falls back to a plain heuristic so the rest of the
app still works for a demo.

### Data model

- `HCP` — the doctor/pharmacist being visited
- `Interaction` — one logged conversation (form or chat), with LLM-derived `summary`, `topics_discussed`, `sentiment`, `entities`
- `FollowUp` — action items generated from an interaction

Defaults to **SQLite** for zero-setup local running. Swap in Postgres or
MySQL by setting `DATABASE_URL` in `backend/.env` — no code changes needed,
SQLAlchemy handles the dialect.

---

## Running it locally

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # then add your GROQ_API_KEY
uvicorn app.main:app --reload --port 8000
```

Get a free Groq API key at https://console.groq.com — the app uses
`gemma2-9b-it` by default (`llama-3.3-70b-versatile` is available as a
configurable fallback for heavier reasoning).

API docs available at `http://localhost:8000/docs` once running.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm start
```

Opens at `http://localhost:3000`. Uses a fixed demo HCP id
(`demo-hcp-1`) out of the box — create that HCP first via the API docs
(`POST /hcps/`) or adjust `REACT_APP_DEMO_HCP_ID` to an id you've created.

### Quick smoke test without the UI

```bash
curl -X POST http://localhost:8000/hcps/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Dr. Rao", "specialty": "Cardiology"}'

curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"hcp_id": "<id from above>", "message": "Just met Dr. Rao, discussed Cardivex dosing for elderly patients, she seemed positive and wants samples next week"}'
```

---

## Notes / scope

This is a prototype built to demonstrate the architecture and agent design
called for in the assignment, not a production system. Things I'd harden
before shipping: auth on the API, input validation beyond Pydantic defaults,
rate limiting on the LLM calls, retry/observability around the Groq calls,
and a proper multi-tenant HCP/rep model instead of the single demo HCP id
used in the frontend for simplicity.
