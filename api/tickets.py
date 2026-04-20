"""
Moviroo AI Chatbot - Tickets API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import logging

from database.connection import get_db
from database.models import Ticket
from pipelines.training_pipeline import training_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["Tickets"])


class TicketCreate(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    category: Optional[str] = None
    language: str = "en"


class TicketResolve(BaseModel):
    answer: str = Field(..., min_length=1)
    category: Optional[str] = None


class TicketOut(BaseModel):
    ticket_id: str
    question: str
    answer: Optional[str]
    category: Optional[str]
    language: str
    status: str
    confidence_score: Optional[float]

    class Config:
        from_attributes = True


@router.post("/", response_model=TicketOut, summary="Create a support ticket")
async def create_ticket(body: TicketCreate, db: AsyncSession = Depends(get_db)):
    ticket = Ticket(
        question=body.question,
        session_id=body.session_id,
        category=body.category,
        language=body.language,
        status="open",
        source="manual",
    )
    db.add(ticket)
    await db.flush()
    return ticket


@router.get("/", response_model=List[TicketOut], summary="List tickets")
async def list_tickets(
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    q = select(Ticket).limit(limit).order_by(Ticket.created_at.desc())
    if status:
        q = q.where(Ticket.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{ticket_id}", response_model=TicketOut, summary="Get a ticket")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}/resolve", response_model=TicketOut, summary="Resolve a ticket")
async def resolve_ticket(
    ticket_id: str,
    body: TicketResolve,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.answer = body.answer
    ticket.status = "resolved"
    if body.category:
        ticket.category = body.category
    await db.flush()

    # Add resolved ticket to FAISS index incrementally
    added = training_pipeline.add_single_ticket(ticket)
    if added:
        ticket.indexed = True
        logger.info(f"Ticket {ticket_id} indexed in FAISS")

    return ticket
