"""
Moviroo AI Chatbot - Health and Stats API Routes
System health checks and statistics endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from api.schemas import HealthResponse, StatsResponse
from database.connection import get_db_session
from services.chatbot import chatbot_service
from services.ticket import ticket_service
from services.feedback import feedback_service
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health & Stats"])


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """
    Health check endpoint

    Returns:
    - System status
    - Application version
    - Database connectivity
    - Vector store statistics
    - Current timestamp
    """
    try:
        await db.execute("SELECT 1")
        db_status = "connected"
        vector_stats = chatbot_service.get_stats()

        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            timestamp=datetime.now().isoformat(),
            database=db_status,
            vector_store=vector_stats['vector_store']
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@router.get("/stats", response_model=StatsResponse, status_code=status.HTTP_200_OK)
async def get_stats(db: AsyncSession = Depends(get_db_session)):
    """Get comprehensive system statistics"""
    try:
        chatbot_stats = chatbot_service.get_stats()
        ticket_stats = await ticket_service.get_ticket_stats(db)
        feedback_stats = await feedback_service.get_feedback_stats(db, days=30)
        return StatsResponse(
            chatbot=chatbot_stats,
            tickets=ticket_stats,
            feedback=feedback_stats
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/info", status_code=status.HTTP_200_OK)
async def get_system_info():
    """Get system configuration information"""
    return {
        'app_name': settings.app_name,
        'version': settings.app_version,
        'environment': settings.environment,
        'supported_languages': settings.supported_languages_list,
        'embedding_model': settings.embedding_model,
        'similarity_threshold': settings.similarity_threshold,
        'auto_learning_enabled': settings.auto_learning_enabled,
        'features': {
            'multilingual': True,
            'semantic_search': True,
            'incremental_learning': settings.auto_learning_enabled,
            'feedback_system': True,
            'ticket_system': True,
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
#  ADMIN – Entraînement depuis CSV + tickets BD
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/admin/train", status_code=status.HTTP_200_OK)
async def train_model(
    force_rebuild: bool = True,
    db: AsyncSession = Depends(get_db_session)
):
    """
    🚀 **Lance l'entraînement complet du modèle** (admin)

    ## Flux d'entraînement :
    1. Lit **dataset.csv** local → source primaire
    2. Charge les **tickets résolus** depuis la BD → enrichissement
    3. Fusionne + déduplique les deux sources
    4. Génère les embeddings via SentenceTransformers
    5. Reconstruit l'index FAISS et le sauvegarde

    ## Paramètres :
    - **force_rebuild** (défaut: True) : reconstruction complète.
      Si False → ajout incrémental des nouveaux tickets uniquement.

    ## Retour :
    - Rapport complet de la session d'entraînement
    - Statistiques CSV, tickets, déduplication, index FAISS
    """
    try:
        from pipelines.training_pipeline import training_pipeline

        logger.info(
            f"🎓 Entraînement demandé (force_rebuild={force_rebuild})"
        )

        report = await training_pipeline.run(db=db, force_rebuild=force_rebuild)

        return {
            "message": "Entraînement terminé avec succès" if report.success
                       else "Entraînement échoué",
            "success": report.success,
            "report": report.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erreur endpoint /admin/train : {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entraînement échoué : {str(e)}"
        )


@router.get("/admin/train/status", status_code=status.HTTP_200_OK)
async def get_training_status():
    """
    📊 **Statut de l'index d'entraînement** (admin)

    Retourne l'état actuel de l'index FAISS sans relancer l'entraînement.

    ## Retour :
    - Si l'index est chargé
    - Nombre total de vecteurs
    - Répartition par source (csv vs tickets)
    - Chemin vers dataset.csv (et s'il existe)
    """
    try:
        from pipelines.training_pipeline import training_pipeline
        status_info = training_pipeline.get_index_status()
        return {
            "status": "ok",
            "index": status_info,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/admin/rebuild-index", status_code=status.HTTP_200_OK)
async def rebuild_index(db: AsyncSession = Depends(get_db_session)):
    """
    🔄 **Reconstruit l'index FAISS complet** (admin)

    Alias de `/admin/train?force_rebuild=true`.
    Utilise le nouveau pipeline d'entraînement (CSV + tickets).
    """
    try:
        from pipelines.training_pipeline import training_pipeline
        report = await training_pipeline.run(db=db, force_rebuild=True)

        return {
            'message': 'Index reconstruit avec succès' if report.success else 'Reconstruction échouée',
            'success': report.success,
            'total_vectors': report.vectors_indexed,
            'from_csv': report.final_from_csv,
            'from_tickets': report.final_from_tickets,
            'duplicates_removed': report.duplicates_removed,
            'timestamp': datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Erreur rebuild-index: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reconstruction échouée : {str(e)}"
        )


@router.post("/admin/load-dataset", status_code=status.HTTP_200_OK)
async def load_dataset(db: AsyncSession = Depends(get_db_session)):
    """
    📂 **Charge dataset.csv dans la KnowledgeBase** (admin)

    - Lit le CSV local
    - Importe les nouvelles entrées (ignore les doublons)
    - Ne reconstruit PAS l'index FAISS (utilisez `/admin/train` pour ça)
    """
    try:
        from pipelines.data_loader import data_loader
        count = await data_loader.load_initial_dataset(db)
        return {
            'message': 'Dataset chargé avec succès',
            'entries_loaded': count,
            'tip': 'Lancez /admin/train pour reconstruire l\'index FAISS',
            'timestamp': datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Erreur load-dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chargement échoué : {str(e)}"
        )
