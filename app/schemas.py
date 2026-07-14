import datetime as dt
from typing import Optional, List, Any
from pydantic import BaseModel


class HCPBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    institution: Optional[str] = None


class HCPCreate(HCPBase):
    pass


class HCPOut(HCPBase):
    id: str

    class Config:
        from_attributes = True


class InteractionCreate(BaseModel):
    hcp_id: str
    interaction_type: str = "visit"
    channel: str = "structured"
    raw_notes: Optional[str] = None
    summary: Optional[str] = None
    topics_discussed: Optional[List[str]] = None
    sentiment: Optional[str] = None
    entities: Optional[dict] = None
    hcp_name: Optional[str] = None
    attendees: Optional[List[str]] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    suggested_followups: Optional[List[str]] = None


class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    raw_notes: Optional[str] = None
    summary: Optional[str] = None
    topics_discussed: Optional[List[str]] = None
    sentiment: Optional[str] = None
    entities: Optional[dict] = None
    hcp_name: Optional[str] = None
    attendees: Optional[List[str]] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    suggested_followups: Optional[List[str]] = None


class InteractionOut(BaseModel):
    id: str
    hcp_id: str
    interaction_type: str
    channel: str
    raw_notes: Optional[str]
    summary: Optional[str]
    topics_discussed: Optional[List[str]]
    sentiment: Optional[str]
    entities: Optional[dict]
    hcp_name: Optional[str] = None
    attendees: Optional[List[str]] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    suggested_followups: Optional[List[str]] = None
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    hcp_id: str
    message: str
    interaction_id: Optional[str] = None  # set when continuing/editing an existing log


class ChatResponse(BaseModel):
    reply: str
    tool_calls: List[str] = []
    interaction: Optional[InteractionOut] = None
