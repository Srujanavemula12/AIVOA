from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas
from .database import engine, get_db
from .agent import run_agent

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AIVOA CRM - HCP Interaction Module")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only - lock this down for real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- HCPs -------------------------------------------------------------
@app.post("/hcps/", response_model=schemas.HCPOut)
def create_hcp(hcp: schemas.HCPCreate, db: Session = Depends(get_db)):
    db_hcp = models.HCP(**hcp.model_dump())
    db.add(db_hcp)
    db.commit()
    db.refresh(db_hcp)
    return db_hcp


@app.get("/hcps/", response_model=list[schemas.HCPOut])
def list_hcps(db: Session = Depends(get_db)):
    return db.query(models.HCP).all()


# --- Interactions (structured form path) -------------------------------
@app.post("/interactions/", response_model=schemas.InteractionOut)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    interaction = models.Interaction(**payload.model_dump())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


@app.get("/interactions/", response_model=list[schemas.InteractionOut])
def list_interactions(hcp_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Interaction)
    if hcp_id:
        q = q.filter(models.Interaction.hcp_id == hcp_id)
    return q.order_by(models.Interaction.created_at.desc()).all()


@app.put("/interactions/{interaction_id}", response_model=schemas.InteractionOut)
def update_interaction(interaction_id: str, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    interaction = db.get(models.Interaction, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(interaction, field, value)
    db.commit()
    db.refresh(interaction)
    return interaction


@app.delete("/interactions/{interaction_id}")
def delete_interaction(interaction_id: str, db: Session = Depends(get_db)):
    interaction = db.get(models.Interaction, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    db.delete(interaction)
    db.commit()
    return {"status": "deleted"}


# --- Conversational path (LangGraph agent) ------------------------------
@app.post("/agent/chat", response_model=schemas.ChatResponse)
def agent_chat(payload: schemas.ChatMessage, db: Session = Depends(get_db)):
    contextual_message = f"[hcp_id={payload.hcp_id}] {payload.message}"
    if payload.interaction_id:
        contextual_message += f" [interaction_id={payload.interaction_id}]"
    try:
        result = run_agent(db, contextual_message)
    except Exception as e:
        return schemas.ChatResponse(reply=f"Sorry, I hit an error processing that: {str(e)}", tool_calls=[], interaction=None)
    latest_interaction = None
    if payload.interaction_id:
        latest_interaction = db.get(models.Interaction, payload.interaction_id)
    else:
        latest_interaction = (
            db.query(models.Interaction)
            .filter(models.Interaction.hcp_id == payload.hcp_id)
            .order_by(models.Interaction.created_at.desc())
            .first()
        )

    return schemas.ChatResponse(
        reply=result["reply"],
        tool_calls=result["tool_calls"],
        interaction=latest_interaction,
    )


@app.get("/")
def root():
    return {"status": "ok", "service": "AIVOA CRM HCP Module API"}
