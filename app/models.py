import uuid
import datetime as dt

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .database import Base


def gen_id():
    return str(uuid.uuid4())


class HCP(Base):
    """A Healthcare Professional (doctor, pharmacist, etc.) the field rep engages with."""
    __tablename__ = "hcps"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    institution = Column(String, nullable=True)

    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")


class Interaction(Base):
    """A single logged interaction between a rep and an HCP."""
    __tablename__ = "interactions"

    id = Column(String, primary_key=True, default=gen_id)
    hcp_id = Column(String, ForeignKey("hcps.id"), nullable=False)

    interaction_type = Column(String, default="visit")  # visit, call, email, conference
    channel = Column(String, default="structured")       # structured | chat
    raw_notes = Column(Text, nullable=True)               # original free text (if via chat)

    summary = Column(Text, nullable=True)                 # LLM-generated summary
    topics_discussed = Column(JSON, nullable=True)         # list[str], e.g. drug names
    sentiment = Column(String, nullable=True)              # positive / neutral / negative
    entities = Column(JSON, nullable=True)                 # structured extraction result

    # Fields matching the "Log HCP Interaction" screen mockup
    hcp_name = Column(String, nullable=True)                # denormalized for quick display
    attendees = Column(JSON, nullable=True)                 # list[str]
    materials_shared = Column(JSON, nullable=True)           # list[str]
    samples_distributed = Column(JSON, nullable=True)        # list[str]
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)          # free-text rep-entered follow-ups
    suggested_followups = Column(JSON, nullable=True)        # list[str] - AI-suggested, separate from the above

    created_at = Column(DateTime, default=dt.datetime.utcnow)

    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")
    followups = relationship("FollowUp", back_populates="interaction", cascade="all, delete-orphan")


class FollowUp(Base):
    """A follow-up task generated from an interaction (e.g. 'send samples next week')."""
    __tablename__ = "followups"

    id = Column(String, primary_key=True, default=gen_id)
    interaction_id = Column(String, ForeignKey("interactions.id"), nullable=False)

    description = Column(Text, nullable=False)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default="open")  # open / done

    interaction = relationship("Interaction", back_populates="followups")
