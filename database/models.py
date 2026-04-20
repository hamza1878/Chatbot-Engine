"""
Moviroo AI Chatbot - Database Models
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
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    language = Column(String(20), default="en")
    status = Column(String(20), default="open")   # open | resolved | closed
    confidence_score = Column(Float, nullable=True)
    session_id = Column(String(100), nullable=True)
    source = Column(String(30), default="chatbot")  # chatbot | manual
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    indexed = Column(Boolean, default=False)       # added to FAISS?


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), nullable=True, index=True)
    session_id = Column(String(100), nullable=True)
    rating = Column(Integer, nullable=False)       # 1-5
    comment = Column(Text, nullable=True)
    helpful = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
