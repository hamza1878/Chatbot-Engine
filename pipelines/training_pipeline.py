"""
Moviroo AI Chatbot - Training Pipeline
Loads dataset.csv + resolved tickets → builds FAISS index
"""
import os
import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.embedding import embedding_service
from models.vector_store import FAISSVectorStore, vector_store as global_store

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"question", "answer", "category", "language"}

SAMPLE_DATA = [
    ("My payment failed", "Check card funds, details, and expiry. Try another method.", "payment", "en"),
    ("How do I book a ride", "Open Moviroo, enter destination, choose type, confirm pickup.", "booking", "en"),
    ("I forgot my password", "Tap Forgot Password, enter email, check inbox, create new password.", "password", "en"),
    ("App is crashing", "Force-close, update the app, restart your phone, clear cache.", "bug", "en"),
    ("Driver is late", "Track driver on map. Call via app. Cancel free if 10+ min late.", "ride_delay", "en"),
    ("Mon paiement a échoué", "Vérifiez le solde, les détails et la validité de votre carte.", "payment", "fr"),
    ("Comment réserver une course", "Ouvrez Moviroo, entrez la destination, choisissez le type.", "booking", "fr"),
    ("Mot de passe oublié", "Appuyez sur Mot de passe oublié et suivez les instructions.", "password", "fr"),
    ("فشل الدفع", "تحقق من الرصيد وتفاصيل البطاقة. جرب طريقة دفع أخرى.", "payment", "ar"),
    ("كيف أحجز رحلة", "افتح Moviroo، أدخل وجهتك، اختر نوع الرحلة وأكد.", "booking", "ar"),
    ("machkel fil paiement", "Verifi carte: rséd, détails, w validité. Jrreb méthode okhra.", "payment", "fr-ar"),
    ("kifech na3mel réservation", "I7lel Moviroo, okthob destination, doboz Request.", "booking", "fr-ar"),
]


@dataclass
class TrainingReport:
    success: bool = False
    vectors_indexed: int = 0
    final_from_csv: int = 0
    final_from_tickets: int = 0
    duplicates_removed: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return self.__dict__


class TrainingPipeline:

    def __init__(self, store: FAISSVectorStore = None):
        self.store = store or global_store

    # ── Public API ───────────────────────────────────────────────────────

    async def run(self, db: AsyncSession, force_rebuild: bool = True) -> TrainingReport:
        t0 = datetime.now()
        report = TrainingReport()
        try:
            csv_data = self._load_csv()
            ticket_data = await self._load_tickets(db)

            all_data = self._merge_deduplicate(csv_data, ticket_data)
            report.final_from_csv = len(csv_data)
            report.final_from_tickets = len(ticket_data)
            report.duplicates_removed = (len(csv_data) + len(ticket_data)) - len(all_data)

            self.store.rebuild(all_data, embedding_service)

            report.vectors_indexed = self.store.index.ntotal if self.store.index else 0
            report.success = True
            logger.info(f"Training done: {report.vectors_indexed} vectors in {(datetime.now()-t0).total_seconds():.1f}s")

        except Exception as e:
            report.error = str(e)
            logger.error(f"Training failed: {e}")

        report.duration_seconds = (datetime.now() - t0).total_seconds()
        return report

    def add_single_ticket(self, ticket) -> bool:
        """Add one resolved ticket incrementally. Call after resolving a ticket."""
        try:
            if embedding_service.model is None:
                embedding_service.load_model()
            added = self.store.add_ticket(ticket, embedding_service)
            if added:
                self.store.save()
            return added
        except Exception as e:
            logger.error(f"add_single_ticket error: {e}")
            return False

    # ── Internal ─────────────────────────────────────────────────────────

    def _load_csv(self) -> List[Dict[str, Any]]:
        csv_path = os.path.join(settings.data_dir, "dataset.csv")

        if not os.path.exists(csv_path):
            logger.warning("dataset.csv not found — using built-in samples")
            return [
                {"question": q, "answer": a, "category": c, "language": l, "source": "knowledge_base"}
                for q, a, c, l in SAMPLE_DATA
            ]

        rows = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
                logger.error(f"CSV missing columns. Found: {reader.fieldnames}")
                return []
            for row in reader:
                q = (row.get("question") or "").strip()
                a = (row.get("answer") or "").strip()
                if q and a:
                    rows.append({
                        "question": q,
                        "answer": a,
                        "category": (row.get("category") or "general").strip(),
                        "language": (row.get("language") or "en").strip(),
                        "source": "knowledge_base",
                    })

        logger.info(f"CSV loaded: {len(rows)} rows")
        return rows

    async def _load_tickets(self, db: AsyncSession) -> List[Dict[str, Any]]:
        try:
            from database.models import Ticket
            result = await db.execute(
                select(Ticket).where(
                    and_(
                        Ticket.status == "resolved",
                        Ticket.answer.isnot(None),
                        Ticket.answer != "",
                    )
                )
            )
            tickets = result.scalars().all()
            rows = [
                {
                    "question": t.question,
                    "answer": t.answer,
                    "category": t.category or "general",
                    "language": t.language or "en",
                    "source": "ticket",
                    "id": t.id,
                }
                for t in tickets
                if t.question and t.answer
            ]
            logger.info(f"Tickets loaded: {len(rows)} resolved")
            return rows
        except Exception as e:
            logger.warning(f"Could not load tickets: {e}")
            return []

    @staticmethod
    def _merge_deduplicate(
        csv_data: List[Dict], ticket_data: List[Dict]
    ) -> List[Dict]:
        seen: set = set()
        result: List[Dict] = []
        # Tickets first (higher priority, more recent)
        for item in ticket_data + csv_data:
            key = item["question"].strip().lower()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result


training_pipeline = TrainingPipeline()
if __name__ == "__main__":
    import asyncio

    async def main():
        print("=" * 55)
        print("   Moviroo — Training Pipeline")
        print("=" * 55)

        # Load embedding model
        from models.embedding import embedding_service
        print("Loading embedding model...")
        embedding_service.load_model()
        print("Model loaded.")

        # Try DB, fallback to CSV-only
        try:
            from database.connection import init_db, AsyncSessionLocal
            await init_db()
            async with AsyncSessionLocal() as db:
                report = await training_pipeline.run(db=db, force_rebuild=True)
        except Exception as e:
            print(f"DB unavailable ({e}) — CSV-only mode")
            from unittest.mock import AsyncMock, MagicMock
            mock_db = AsyncMock()
            mock_res = MagicMock()
            mock_res.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_res
            report = await training_pipeline.run(db=mock_db, force_rebuild=True)

        # Print report
        print("\n--- Report ---")
        print(f"Success        : {report.success}")
        print(f"Vectors indexed: {report.vectors_indexed}")
        print(f"From CSV       : {report.final_from_csv}")
        print(f"From tickets   : {report.final_from_tickets}")
        print(f"Duplicates rm  : {report.duplicates_removed}")
        print(f"Duration       : {report.duration_seconds:.1f}s")
        if report.error:
            print(f"Error          : {report.error}")

        if report.success:
            print("\nIndex saved to models_data/")
            print("You can now run: python main.py")
        else:
            print("\nTraining failed. Check logs above.")

    asyncio.run(main())