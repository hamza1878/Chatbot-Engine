"""
Moviroo AI Chatbot - Feedback API
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.connection import get_db
from database.models import Feedback

router = APIRouter(prefix="/feedback", tags=["Feedback"])


class FeedbackCreate(BaseModel):
    ticket_id: Optional[str] = None
    session_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    helpful: Optional[bool] = None
    comment: Optional[str] = None


@router.post("/", summary="Submit feedback")
async def submit_feedback(body: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    fb = Feedback(
        ticket_id=body.ticket_id,
        session_id=body.session_id,
        rating=body.rating,
        helpful=body.helpful,
        comment=body.comment,
    )
    db.add(fb)
    await db.flush()
    return {"status": "ok", "message": "Feedback recorded. Thank you!"}
