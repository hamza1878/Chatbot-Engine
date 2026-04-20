"""
Moviroo AI Chatbot - Chat API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from database.connection import get_db
from database.models import Ticket
from core.rag_pipeline import rag_pipeline
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    category: str
    language: str
    source: str          # direct_match | rag_llm | fallback
    suggest_ticket: bool
    session_id: str


@router.post("/", response_model=ChatResponse, summary="Send a message to the chatbot")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = await rag_pipeline.run(req.message)

    # Auto-create ticket if confidence is low
    if result.suggest_ticket:
        ticket = Ticket(
            question=req.message,
            category=result.category if result.category != "unknown" else None,
            language=result.language,
            confidence_score=result.confidence,
            session_id=req.session_id,
            source="chatbot",
            status="open",
        )
        db.add(ticket)
        await db.flush()
        logger.info(f"Auto-ticket created: {ticket.ticket_id}")

    return ChatResponse(
        answer=result.answer,
        confidence=result.confidence,
        category=result.category,
        language=result.language,
        source=result.source,
        suggest_ticket=result.suggest_ticket,
        session_id=req.session_id,
    )
