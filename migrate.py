"""
Moviroo AI Chatbot - Database Models
Matches existing PostgreSQL schema
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from database.connection import Base
import uuid


def gen_ticket_id():
    return f"TKT-{uuid.uuid4().hex[:8].upper()}"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), unique=True, default=gen_ticket_id, index=True)
    user_id = Column(String(100), nullable=True)        # existing column
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    language = Column(String(10), default="en")
    status = Column(String(20), default="open")
    priority = Column(String(20), default="normal")     # existing column
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)  # existing
    admin_id = Column(String(100), nullable=True)       # existing column
    resolution_time_minutes = Column(Integer, nullable=True)      # existing
    embedding_vector = Column(Text, nullable=True)      # existing column

    # New columns (added by migration above)
    confidence_score = Column(Float, nullable=True)
    session_id = Column(String(100), nullable=True)
    source = Column(String(30), default="chatbot")
    indexed = Column(Boolean, default=False)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), nullable=True, index=True)
    session_id = Column(String(100), nullable=True)
    rating = Column(Integer, nullable=False)
    helpful = Column(Boolean, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())