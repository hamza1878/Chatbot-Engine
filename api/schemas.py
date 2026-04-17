"""
Moviroo AI Chatbot - API Schemas
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# Chat Schemas
# ============================================================================

class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID")
    language: Optional[str] = Field(None, description="Optional language hint")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class Alternative(BaseModel):
    """Alternative answer schema"""
    answer: str
    score: float
    category: Optional[str]


class ChatResponse(BaseModel):
    """Response schema for chat endpoint"""
    response: str
    confidence_score: float
    detected_language: str
    detected_category: Optional[str]
    matched_source: str
    matched_id: Optional[int]
    response_time_ms: int
    conversation_id: str
    timestamp: str
    suggestions: Optional[List[str]] = None
    alternatives: Optional[List[Alternative]] = None


# ============================================================================
# Ticket Schemas
# ============================================================================

class TicketCreateRequest(BaseModel):
    """Request schema for creating a ticket"""
    user_id: str = Field(..., min_length=1, description="User ID")
    question: str = Field(..., min_length=10, max_length=2000, description="User question/issue")
    category: Optional[str] = Field(None, description="Optional category")
    language: Optional[str] = Field('en', description="Language code")


class TicketUpdateRequest(BaseModel):
    """Request schema for updating a ticket"""
    answer: Optional[str] = Field(None, description="Admin answer")
    status: Optional[str] = Field(None, description="Ticket status")
    priority: Optional[str] = Field(None, description="Ticket priority")
    admin_id: Optional[str] = Field(None, description="Admin user ID")
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['open', 'in_progress', 'resolved', 'closed']
            if v not in valid_statuses:
                raise ValueError(f'Status must be one of: {valid_statuses}')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None:
            valid_priorities = ['low', 'medium', 'high', 'critical']
            if v not in valid_priorities:
                raise ValueError(f'Priority must be one of: {valid_priorities}')
        return v


class TicketResponse(BaseModel):
    """Response schema for ticket"""
    id: int
    ticket_id: str
    user_id: str
    question: str
    answer: Optional[str]
    category: Optional[str]
    language: str
    status: str
    priority: str
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolution_time_minutes: Optional[int]
    
    class Config:
        from_attributes = True


# ============================================================================
# Feedback Schemas
# ============================================================================

class FeedbackRequest(BaseModel):
    """Request schema for submitting feedback"""
    conversation_id: str = Field(..., description="Conversation ID")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    feedback_type: str = Field(..., description="Type of feedback")
    user_message: str = Field(..., description="Original user message")
    bot_response: str = Field(..., description="Bot response")
    comment: Optional[str] = Field(None, max_length=500, description="Optional comment")
    message_id: Optional[int] = Field(None, description="Optional message ID")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    
    @validator('feedback_type')
    def validate_feedback_type(cls, v):
        valid_types = [
            'helpful',
            'not_helpful',
            'wrong_answer',
            'incomplete_answer',
            'good_response',
            'needs_improvement'
        ]
        if v not in valid_types:
            raise ValueError(f'Feedback type must be one of: {valid_types}')
        return v


class FeedbackResponse(BaseModel):
    """Response schema for feedback"""
    id: int
    conversation_id: str
    rating: int
    feedback_type: str
    comment: Optional[str]
    created_at: datetime
    is_processed: bool
    
    class Config:
        from_attributes = True


# ============================================================================
# Statistics Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    database: str
    vector_store: Dict[str, Any]


class StatsResponse(BaseModel):
    """General statistics response"""
    chatbot: Dict[str, Any]
    tickets: Dict[str, Any]
    feedback: Dict[str, Any]


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    timestamp: str
