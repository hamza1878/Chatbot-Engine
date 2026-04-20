"""
Moviroo AI Chatbot - Health & Stats API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from database.connection import get_db
from database.models import Ticket, Feedback
from models.vector_store import vector_store
from config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now().isoformat(),
        "faiss_vectors": vector_store.index.ntotal if vector_store.index else 0,
        "embedding_model": settings.embedding_model,
        "llm_model": settings.ollama_model,
    }


@router.get("/stats", summary="System statistics")
async def stats(db: AsyncSession = Depends(get_db)):
    total_tickets = (await db.execute(select(func.count(Ticket.id)))).scalar()
    open_tickets = (await db.execute(
        select(func.count(Ticket.id)).where(Ticket.status == "open")
    )).scalar()
    resolved_tickets = (await db.execute(
        select(func.count(Ticket.id)).where(Ticket.status == "resolved")
    )).scalar()
    avg_score = (await db.execute(select(func.avg(Feedback.rating)))).scalar()

    return {
        "faiss": vector_store.stats(),
        "tickets": {
            "total": total_tickets,
            "open": open_tickets,
            "resolved": resolved_tickets,
        },
        "feedback": {
            "average_rating": round(float(avg_score or 0), 2),
        },
        "config": {
            "high_confidence_threshold": settings.high_confidence_threshold,
            "low_confidence_threshold": settings.low_confidence_threshold,
            "top_k": settings.top_k_results,
        },
    }


@router.post("/admin/rebuild-index", summary="Force rebuild FAISS index")
async def rebuild_index(db: AsyncSession = Depends(get_db)):
    from pipelines.training_pipeline import training_pipeline
    from models.embedding import embedding_service
    if embedding_service.model is None:
        embedding_service.load_model()
    report = await training_pipeline.run(db=db, force_rebuild=True)
    return report.to_dict()
