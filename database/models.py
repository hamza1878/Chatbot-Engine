"""
Moviroo AI Chatbot - Database Models
SQLAlchemy ORM models for tickets, feedback, conversations, and analytics
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Ticket(Base):
    """Support tickets submitted by users"""
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    
    # Ticket content
    question = Column(Text, nullable=False)
    category = Column(String(50), nullable=True, index=True)
    language = Column(String(10), default="en", index=True)
    
    # Admin response
    answer = Column(Text, nullable=True)
    status = Column(String(20), default="open", index=True)  # open, in_progress, resolved, closed
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    admin_id = Column(String(100), nullable=True)
    
    # Analytics
    resolution_time_minutes = Column(Integer, nullable=True)
    embedding_vector = Column(Text, nullable=True)  # Stored as JSON string
    
    # Relationships
    feedbacks = relationship("Feedback", back_populates="ticket", cascade="all, delete-orphan")
    conversation_messages = relationship("ConversationMessage", back_populates="related_ticket")
    
    __table_args__ = (
        Index('idx_ticket_status_created', 'status', 'created_at'),
        Index('idx_ticket_category_language', 'category', 'language'),
    )
    
    def __repr__(self):
        return f"<Ticket(id={self.ticket_id}, status={self.status}, category={self.category})>"


class KnowledgeBase(Base):
    """Pre-defined Q&A from dataset.csv"""
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    language = Column(String(10), default="en", index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True, index=True)
    
    # Analytics
    usage_count = Column(Integer, default=0)
    avg_confidence_score = Column(Float, default=0.0)
    embedding_vector = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_kb_category_active', 'category', 'is_active'),
    )
    
    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, category={self.category})>"


class Conversation(Base):
    """User conversation sessions"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    
    # Metadata
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Analytics
    total_messages = Column(Integer, default=0)
    avg_confidence = Column(Float, default=0.0)
    user_satisfaction = Column(Integer, nullable=True)  # 1-5 rating
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.conversation_id}, user={self.user_id})>"


class ConversationMessage(Base):
    """Individual messages in a conversation"""
    __tablename__ = "conversation_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(100), ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    
    # Message content
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    detected_language = Column(String(10), default="en")
    detected_category = Column(String(50), nullable=True)
    
    # AI metadata
    confidence_score = Column(Float, nullable=True)
    matched_source = Column(String(20), nullable=True)  # 'knowledge_base', 'ticket', 'fallback'
    matched_id = Column(Integer, nullable=True)
    
    # Ticket reference
    related_ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    related_ticket = relationship("Ticket", back_populates="conversation_messages")
    
    __table_args__ = (
        Index('idx_msg_conversation_created', 'conversation_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Message(conversation={self.conversation_id}, confidence={self.confidence_score})>"


class Feedback(Base):
    """User feedback on chatbot responses"""
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(100), nullable=False, index=True)
    message_id = Column(Integer, nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    
    # Feedback data
    rating = Column(Integer, nullable=False)  # 1-5 stars
    feedback_type = Column(String(20), nullable=False)  # helpful, not_helpful, wrong_answer, etc.
    comment = Column(Text, nullable=True)
    
    # Context
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(String(100), nullable=True, index=True)
    
    # Processing
    is_processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    ticket = relationship("Ticket", back_populates="feedbacks")
    
    __table_args__ = (
        Index('idx_feedback_rating_created', 'rating', 'created_at'),
        Index('idx_feedback_processed', 'is_processed', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Feedback(id={self.id}, rating={self.rating}, type={self.feedback_type})>"


class Analytics(Base):
    """Daily analytics and metrics"""
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, unique=True, index=True)
    
    # Volume metrics
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    total_tickets = Column(Integer, default=0)
    total_feedback = Column(Integer, default=0)
    
    # Quality metrics
    avg_confidence_score = Column(Float, default=0.0)
    avg_response_time_ms = Column(Float, default=0.0)
    avg_user_satisfaction = Column(Float, default=0.0)
    
    # Category distribution (JSON string)
    category_distribution = Column(Text, nullable=True)
    language_distribution = Column(Text, nullable=True)
    
    # Resolution metrics
    avg_ticket_resolution_minutes = Column(Float, default=0.0)
    ticket_resolution_rate = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Analytics(date={self.date}, conversations={self.total_conversations})>"
