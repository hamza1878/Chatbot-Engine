"""
Moviroo AI Chatbot - Training Pipeline
=======================================================
FLUX D'ENTRAÎNEMENT:
  1. Lit dataset.csv LOCAL  → source primaire obligatoire
  2. Lit tickets résolus BD → source secondaire optionnelle
  3. Fusionne + déduplique les deux sources
  4. Génère les embeddings via SentenceTransformers
  5. Construit / met à jour l'index FAISS
  6. Sauvegarde l'index sur disque
  7. Retourne un rapport de session complet
=======================================================
"""

import os
import csv
import json
import hashlib
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database.models import KnowledgeBase, Ticket
from models.embedding import embedding_service
from models.vector_store import FAISSVectorStore
from config import settings

logger = logging.getLogger(__name__)
vector_store = FAISSVectorStore()

# ──────────────────────────────────────────────────────────────────────────────
#  Petite dataclass légère pour représenter un item d'entraînement
# ──────────────────────────────────────────────────────────────────────────────
class TrainingItem:
    """Un item prêt à être encodé et indexé"""

    def __init__(
        self,
        question: str,
        answer: str,
        category: str,
        language: str,
        source: str,          # 'csv' | 'ticket'
        source_id: Any = None,
        ticket_id: str = None,
    ):
        self.question = question.strip()
        self.answer = answer.strip()
        self.category = (category or "general").strip().lower()
        self.language = (language or "en").strip().lower()
        self.source = source
        self.source_id = source_id
        self.ticket_id = ticket_id

        # Empreinte pour la déduplication (question normalisée)
        self.fingerprint = hashlib.md5(
            self.question.lower().encode("utf-8")
        ).hexdigest()

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "source":     self.source,
            "id":         self.source_id,
            "ticket_id":  self.ticket_id,
            "question":   self.question,
            "answer":     self.answer,
            "category":   self.category,
            "language":   self.language,
        }

    def __repr__(self):
        return (
            f"<TrainingItem source={self.source!r} "
            f"category={self.category!r} lang={self.language!r} "
            f"q={self.question[:50]!r}>"
        )


# ──────────────────────────────────────────────────────────────────────────────
#  Rapport de session d'entraînement
# ──────────────────────────────────────────────────────────────────────────────
class TrainingReport:
    """Résumé complet d'une session d'entraînement"""

    def __init__(self):
        self.started_at: str = datetime.now().isoformat()
        self.finished_at: str = ""
        self.success: bool = False
        self.error: str = ""

        # Statistiques CSV
        self.csv_path: str = ""
        self.csv_total_rows: int = 0
        self.csv_valid_rows: int = 0
        self.csv_skipped_rows: int = 0
        self.csv_invalid_rows: int = 0

        # Statistiques Tickets
        self.tickets_found: int = 0
        self.tickets_used: int = 0
        self.tickets_skipped_no_answer: int = 0

        # Après fusion
        self.total_before_dedup: int = 0
        self.total_after_dedup: int = 0
        self.duplicates_removed: int = 0

        # Détail par source
        self.final_from_csv: int = 0
        self.final_from_tickets: int = 0

        # Statistiques FAISS
        self.vectors_indexed: int = 0
        self.index_dimension: int = 0
        self.embedding_model: str = ""

        # Durée
        self.duration_seconds: float = 0.0

    def finish(self, success: bool, error: str = ""):
        self.finished_at = datetime.now().isoformat()
        self.success = success
        self.error = error
        try:
            t0 = datetime.fromisoformat(self.started_at)
            t1 = datetime.fromisoformat(self.finished_at)
            self.duration_seconds = (t1 - t0).total_seconds()
        except Exception:
            pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session": {
                "started_at":       self.started_at,
                "finished_at":      self.finished_at,
                "success":          self.success,
                "error":            self.error,
                "duration_seconds": round(self.duration_seconds, 2),
            },
            "data_sources": {
                "csv": {
                    "path":         self.csv_path,
                    "total_rows":   self.csv_total_rows,
                    "valid_rows":   self.csv_valid_rows,
                    "skipped_rows": self.csv_skipped_rows,
                    "invalid_rows": self.csv_invalid_rows,
                },
                "tickets": {
                    "found":              self.tickets_found,
                    "used":               self.tickets_used,
                    "skipped_no_answer":  self.tickets_skipped_no_answer,
                },
            },
            "deduplication": {
                "total_before": self.total_before_dedup,
                "total_after":  self.total_after_dedup,
                "removed":      self.duplicates_removed,
            },
            "final_dataset": {
                "total":        self.total_after_dedup,
                "from_csv":     self.final_from_csv,
                "from_tickets": self.final_from_tickets,
            },
            "faiss_index": {
                "vectors_indexed": self.vectors_indexed,
                "dimension":       self.index_dimension,
                "embedding_model": self.embedding_model,
            },
        }

    def log_summary(self):
        logger.info("=" * 60)
        logger.info("📊  RAPPORT D'ENTRAÎNEMENT MOVIROO")
        logger.info("=" * 60)
        logger.info(f"  Statut          : {'✅ SUCCESS' if self.success else '❌ FAILED'}")
        if self.error:
            logger.error(f"  Erreur          : {self.error}")
        logger.info(f"  Durée           : {self.duration_seconds:.1f}s")
        logger.info("─" * 60)
        logger.info("  SOURCE CSV")
        logger.info(f"    Fichier        : {self.csv_path}")
        logger.info(f"    Lignes totales : {self.csv_total_rows}")
        logger.info(f"    Lignes valides : {self.csv_valid_rows}")
        logger.info(f"    Ignorées       : {self.csv_skipped_rows}")
        logger.info(f"    Invalides      : {self.csv_invalid_rows}")
        logger.info("─" * 60)
        logger.info("  SOURCE TICKETS (BD)")
        logger.info(f"    Tickets trouvés: {self.tickets_found}")
        logger.info(f"    Tickets utilisés: {self.tickets_used}")
        logger.info(f"    Sans réponse   : {self.tickets_skipped_no_answer}")
        logger.info("─" * 60)
        logger.info("  DÉDUPLICATION")
        logger.info(f"    Avant          : {self.total_before_dedup}")
        logger.info(f"    Après          : {self.total_after_dedup}")
        logger.info(f"    Doublons retirés: {self.duplicates_removed}")
        logger.info("─" * 60)
        logger.info("  DATASET FINAL")
        logger.info(f"    Total          : {self.total_after_dedup}")
        logger.info(f"    Depuis CSV     : {self.final_from_csv}")
        logger.info(f"    Depuis Tickets : {self.final_from_tickets}")
        logger.info("─" * 60)
        logger.info("  INDEX FAISS")
        logger.info(f"    Vecteurs       : {self.vectors_indexed}")
        logger.info(f"    Dimension      : {self.index_dimension}")
        logger.info(f"    Modèle         : {self.embedding_model}")
        logger.info("=" * 60)


# ──────────────────────────────────────────────────────────────────────────────
#  Classe principale : TrainingPipeline
# ──────────────────────────────────────────────────────────────────────────────
class TrainingPipeline:
    """
    Pipeline complet : CSV local  +  tickets résolus BD  →  index FAISS

    Priorités :
      1. dataset.csv  (toujours chargé s'il existe)
      2. Tickets BD   (chargés si disponibles, ajoutés en complément)

    Les tickets NE remplacent PAS le CSV, ils l'enrichissent.
    Si une question du ticket est identique (fingerprint MD5) à une
    question CSV, la version CSV est conservée (source autoritaire).
    """

    # Colonnes requises dans dataset.csv
    REQUIRED_CSV_COLS = {"question", "answer", "category"}

    def __init__(self):
        self.csv_path = os.path.join(settings.data_dir, "dataset.csv")
        self.report = TrainingReport()

    # ──────────────────────────────────────────────────────────────
    #  ÉTAPE 1  –  Lecture du CSV local
    # ──────────────────────────────────────────────────────────────
    def _load_csv(self) -> List[TrainingItem]:
        """
        Lit dataset.csv et retourne une liste de TrainingItem.
        Gère : colonnes manquantes, lignes vides, encodages mixtes.
        """
        self.report.csv_path = self.csv_path
        items: List[TrainingItem] = []

        # ── Fichier absent → crée un dataset d'exemple ──
        if not os.path.exists(self.csv_path):
            logger.warning(
                f"⚠️  dataset.csv introuvable : {self.csv_path}"
                " → création d'un dataset d'exemple"
            )
            self._create_sample_csv()

        logger.info(f"📂 Lecture CSV : {self.csv_path}")

        try:
            df = pd.read_csv(
                self.csv_path,
                encoding="utf-8",
                on_bad_lines="warn",
                dtype=str,           # tout en string pour éviter les NaN numériques
            )
        except UnicodeDecodeError:
            # Fallback latin-1 si utf-8 échoue
            df = pd.read_csv(
                self.csv_path,
                encoding="latin-1",
                on_bad_lines="warn",
                dtype=str,
            )
            logger.warning("⚠️  CSV lu avec encodage latin-1 (fallback)")

        self.report.csv_total_rows = len(df)
        logger.info(f"   {len(df)} lignes trouvées dans le CSV")

        # Vérification colonnes
        missing_cols = self.REQUIRED_CSV_COLS - set(df.columns.str.lower())
        if missing_cols:
            raise ValueError(
                f"❌ Colonnes manquantes dans dataset.csv : {missing_cols}\n"
                f"   Colonnes attendues : question, answer, category\n"
                f"   Colonnes trouvées  : {list(df.columns)}"
            )

        # Normalise les noms de colonnes
        df.columns = df.columns.str.lower().str.strip()

        # Ajoute 'language' si absent
        if "language" not in df.columns:
            df["language"] = "en"
            logger.info("   Colonne 'language' absente → défaut 'en'")

        # Itère sur les lignes
        for idx, row in df.iterrows():
            q = str(row.get("question", "")).strip()
            a = str(row.get("answer", "")).strip()
            cat = str(row.get("category", "general")).strip()
            lang = str(row.get("language", "en")).strip()

            # Ignore lignes vides ou NaN
            if not q or q.lower() in ("nan", "none", "") \
                    or not a or a.lower() in ("nan", "none", ""):
                self.report.csv_invalid_rows += 1
                logger.debug(f"   Ligne {idx+2} ignorée (vide/NaN)")
                continue

            # Ignore lignes déjà en-tête dupliquées
            if q.lower() == "question":
                self.report.csv_skipped_rows += 1
                continue

            items.append(
                TrainingItem(
                    question=q,
                    answer=a,
                    category=cat,
                    language=lang,
                    source="csv",
                    source_id=int(idx),
                )
            )
            self.report.csv_valid_rows += 1

        logger.info(
            f"   ✅ CSV : {self.report.csv_valid_rows} items valides, "
            f"{self.report.csv_invalid_rows} invalides, "
            f"{self.report.csv_skipped_rows} ignorés"
        )
        return items

    # ──────────────────────────────────────────────────────────────
    #  ÉTAPE 2  –  Lecture des tickets résolus (BD)
    # ──────────────────────────────────────────────────────────────
    async def _load_tickets(self, db: AsyncSession) -> List[TrainingItem]:
        """
        Charge tous les tickets avec status='resolved' ET une réponse non-vide.
        Les tickets 'open' ou sans réponse sont ignorés.
        """
        items: List[TrainingItem] = []

        try:
            result = await db.execute(
                select(Ticket).where(
                    and_(
                        Ticket.status == "resolved",
                        Ticket.answer.isnot(None),
                        Ticket.answer != "",
                    )
                ).order_by(Ticket.created_at)
            )
            tickets = result.scalars().all()
            self.report.tickets_found = len(tickets)

            logger.info(f"🎫 Tickets BD : {len(tickets)} tickets résolus trouvés")

            for ticket in tickets:
                q = (ticket.question or "").strip()
                a = (ticket.answer or "").strip()

                if not q or not a:
                    self.report.tickets_skipped_no_answer += 1
                    logger.debug(
                        f"   Ticket {ticket.ticket_id} ignoré (question/réponse vide)"
                    )
                    continue

                items.append(
                    TrainingItem(
                        question=q,
                        answer=a,
                        category=ticket.category or "general",
                        language=ticket.language or "en",
                        source="ticket",
                        source_id=ticket.id,
                        ticket_id=ticket.ticket_id,
                    )
                )
                self.report.tickets_used += 1

            logger.info(
                f"   ✅ Tickets : {self.report.tickets_used} utilisés, "
                f"{self.report.tickets_skipped_no_answer} ignorés (sans réponse)"
            )

        except Exception as e:
            logger.warning(
                f"⚠️  Impossible de charger les tickets BD : {e}\n"
                "   → Entraînement uniquement depuis CSV"
            )

        return items

    # ──────────────────────────────────────────────────────────────
    #  ÉTAPE 3  –  Fusion + Déduplication
    # ──────────────────────────────────────────────────────────────
    def _merge_and_deduplicate(
        self,
        csv_items: List[TrainingItem],
        ticket_items: List[TrainingItem],
    ) -> List[TrainingItem]:
        """
        Règle de fusion :
          - Les items CSV sont prioritaires.
          - Un item ticket est ajouté SEULEMENT si sa question
            (fingerprint MD5) n'existe pas déjà dans le CSV.
        """
        self.report.total_before_dedup = len(csv_items) + len(ticket_items)
        seen_fingerprints: set = set()
        merged: List[TrainingItem] = []

        # 1) Ajoute tous les items CSV en premier (source autoritaire)
        for item in csv_items:
            if item.fingerprint not in seen_fingerprints:
                seen_fingerprints.add(item.fingerprint)
                merged.append(item)

        self.report.final_from_csv = len(merged)

        # 2) Ajoute les tickets non-dupliqués
        ticket_count_before = len(merged)
        for item in ticket_items:
            if item.fingerprint not in seen_fingerprints:
                seen_fingerprints.add(item.fingerprint)
                merged.append(item)
            else:
                logger.debug(
                    f"   Ticket dupliqué ignoré : {item.question[:60]!r}"
                )

        self.report.final_from_tickets = len(merged) - ticket_count_before
        self.report.total_after_dedup = len(merged)
        self.report.duplicates_removed = (
            self.report.total_before_dedup - self.report.total_after_dedup
        )

        logger.info(
            f"🔀 Fusion : {self.report.total_before_dedup} items → "
            f"{self.report.total_after_dedup} après déduplication "
            f"({self.report.duplicates_removed} doublons supprimés)"
        )
        logger.info(
            f"   Depuis CSV     : {self.report.final_from_csv}"
        )
        logger.info(
            f"   Depuis Tickets : {self.report.final_from_tickets}"
        )

        return merged

    # ──────────────────────────────────────────────────────────────
    #  ÉTAPE 4  –  Encodage + construction de l'index FAISS
    # ──────────────────────────────────────────────────────────────
    def _build_faiss_index(self, items: List[TrainingItem]) -> None:
        """
        - Encode toutes les questions en embeddings (batch)
        - Recrée l'index FAISS from scratch
        - Sauvegarde sur disque
        """
        if not items:
            logger.warning("⚠️  Aucun item à indexer – index FAISS non construit")
            return

        logger.info(
            f"🧠 Encodage de {len(items)} questions "
            f"(modèle : {settings.embedding_model}) …"
        )

        questions = [item.question for item in items]

        # Génère tous les embeddings en un seul batch
        embeddings: np.ndarray = embedding_service.encode(
            questions, normalize=True
        )

        logger.info(
            f"   Embeddings générés : shape={embeddings.shape}, "
            f"dtype={embeddings.dtype}"
        )

        # Reconstruit l'index
        vector_store.create_index()

        metadata_list = [item.to_metadata() for item in items]
        vector_store.add_vectors(embeddings, metadata_list)

        # Sauvegarde
        vector_store.save()

        self.report.vectors_indexed = vector_store.index.ntotal
        self.report.index_dimension = vector_store.dimension
        self.report.embedding_model = settings.embedding_model

        logger.info(
            f"💾 Index FAISS sauvegardé : {self.report.vectors_indexed} vecteurs "
            f"({self.report.index_dimension}D)"
        )

    # ──────────────────────────────────────────────────────────────
    #  ÉTAPE 5  –  Sauvegarde des items en BD (KnowledgeBase)
    # ──────────────────────────────────────────────────────────────
    async def _sync_knowledge_base(
        self,
        db: AsyncSession,
        items: List[TrainingItem],
    ) -> None:
        """
        Synchronise la table KnowledgeBase avec les items du CSV.
        Ajoute les nouveaux, ne modifie pas les existants.
        """
        csv_items = [i for i in items if i.source == "csv"]
        new_count = 0

        for item in csv_items:
            result = await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.question == item.question
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                kb = KnowledgeBase(
                    question=item.question,
                    answer=item.answer,
                    category=item.category,
                    language=item.language,
                    is_active=True,
                )
                db.add(kb)
                new_count += 1

        await db.commit()
        logger.info(
            f"🗄️  KnowledgeBase synchronisée : {new_count} nouveaux items ajoutés"
        )

    # ──────────────────────────────────────────────────────────────
    #  POINT D'ENTRÉE PRINCIPAL
    # ──────────────────────────────────────────────────────────────
    async def run(
        self,
        db: AsyncSession,
        force_rebuild: bool = True,
    ) -> TrainingReport:
        """
        Lance le pipeline complet d'entraînement.

        Args:
            db           : session SQLAlchemy async
            force_rebuild: si True, recrée l'index FAISS même s'il existe déjà
                           si False, charge l'index existant et ajoute uniquement
                           les nouveaux tickets non encore indexés

        Returns:
            TrainingReport avec toutes les statistiques
        """
        self.report = TrainingReport()
        logger.info("🚀 Démarrage du pipeline d'entraînement Moviroo …")

        try:
            # ── 1. CSV ──
            csv_items = self._load_csv()

            # ── 2. Tickets BD ──
            ticket_items = await self._load_tickets(db)

            # ── 3. Fusion ──
            all_items = self._merge_and_deduplicate(csv_items, ticket_items)

            if not all_items:
                raise ValueError(
                    "Aucune donnée disponible pour l'entraînement.\n"
                    "  → Vérifiez que data/dataset.csv existe et contient des lignes valides."
                )

            # ── 4. Index FAISS ──
            if force_rebuild or vector_store.index is None or vector_store.index.ntotal == 0:
                self._build_faiss_index(all_items)
            else:
                # Mode incrémental : n'ajoute que les tickets nouveaux
                logger.info(
                    "ℹ️  Mode incrémental : ajout des nouveaux tickets uniquement"
                )
                self._incremental_update(ticket_items)

            # ── 5. Sync KnowledgeBase ──
            await self._sync_knowledge_base(db, all_items)

            # ── Fin succès ──
            self.report.finish(success=True)

        except Exception as exc:
            logger.error(f"❌ Pipeline échoué : {exc}", exc_info=True)
            self.report.finish(success=False, error=str(exc))

        # Affiche le résumé dans les logs
        self.report.log_summary()
        return self.report

    # ──────────────────────────────────────────────────────────────
    #  Mise à jour incrémentale (mode sans rebuild complet)
    # ──────────────────────────────────────────────────────────────
    def _incremental_update(self, ticket_items: List[TrainingItem]) -> None:
        """
        Ajoute uniquement les tickets dont la question n'est pas déjà
        dans l'index (comparaison par fingerprint stocké en metadata).
        """
        existing_fingerprints = {
            hashlib.md5(
                meta.get("question", "").lower().encode("utf-8")
            ).hexdigest()
            for meta in vector_store.metadata
        }

        new_items = [
            item for item in ticket_items
            if item.fingerprint not in existing_fingerprints
        ]

        if not new_items:
            logger.info("   Aucun nouveau ticket à ajouter à l'index")
            return

        logger.info(f"   {len(new_items)} nouveaux tickets à indexer")

        questions = [item.question for item in new_items]
        embeddings = embedding_service.encode(questions, normalize=True)
        metadata_list = [item.to_metadata() for item in new_items]

        vector_store.add_vectors(embeddings, metadata_list)
        vector_store.save()

        self.report.vectors_indexed = vector_store.index.ntotal
        logger.info(
            f"   Index mis à jour : {self.report.vectors_indexed} vecteurs total"
        )

    # ──────────────────────────────────────────────────────────────
    #  Création d'un CSV d'exemple si absent
    # ──────────────────────────────────────────────────────────────
    def _create_sample_csv(self) -> None:
        """Génère un dataset.csv minimal multilingue si le fichier est absent"""
        os.makedirs(settings.data_dir, exist_ok=True)

        sample_rows = [
            # ── English ──────────────────────────────────────────
            ("My payment failed. What should I do?",
             "Check your card balance and details. If the issue persists, "
             "try another payment method or contact your bank.",
             "payment", "en"),
            ("How do I get a refund for my cancelled ride?",
             "Refunds are processed automatically within 5-7 business days "
             "to your original payment method.",
             "payment", "en"),
            ("My driver is late. What can I do?",
             "You can track your driver in real-time on the map, call them "
             "via the app, or cancel for free if they are 10+ minutes late.",
             "ride_delay", "en"),
            ("How do I book a ride?",
             "Open Moviroo → Enter destination → Choose ride type → "
             "Confirm pickup → Tap 'Request Ride'.",
             "booking", "en"),
            ("How do I cancel a ride?",
             "Open your active ride → Tap 'Cancel Ride' → Select reason → "
             "Confirm. Free within 2 minutes of booking.",
             "booking", "en"),
            ("I forgot my password. How do I reset it?",
             "Tap 'Forgot Password' → Enter your email/phone → "
             "Check SMS or email → Click the reset link → Create new password.",
             "password", "en"),
            ("The app keeps crashing. What should I do?",
             "Force-close the app, update to the latest version, restart "
             "your phone, then clear the app cache.",
             "bug", "en"),
            ("How do I create an account?",
             "Download Moviroo → Tap 'Sign Up' → Enter phone number → "
             "Verify OTP → Complete your profile.",
             "account", "en"),
            # ── French ───────────────────────────────────────────
            ("Mon paiement a échoué. Que faire?",
             "Vérifiez le solde et les détails de votre carte. Si le "
             "problème persiste, essayez un autre mode de paiement.",
             "payment", "fr"),
            ("Comment réserver une course?",
             "Ouvrez Moviroo → Entrez la destination → Choisissez le type "
             "→ Confirmez → Appuyez sur 'Demander'.",
             "booking", "fr"),
            ("J'ai oublié mon mot de passe, comment le réinitialiser?",
             "Appuyez sur 'Mot de passe oublié' → Entrez votre email → "
             "Vérifiez votre boîte mail → Cliquez sur le lien.",
             "password", "fr"),
            ("L'application plante souvent. Que faire?",
             "Forcez la fermeture → Mettez à jour l'app → "
             "Redémarrez le téléphone → Videz le cache.",
             "bug", "fr"),
            # ── Arabic ───────────────────────────────────────────
            ("فشل الدفع. ماذا أفعل؟",
             "تحقق من رصيدك وتفاصيل البطاقة. إذا استمرت المشكلة، "
             "جرب طريقة دفع أخرى أو اتصل بالبنك.",
             "payment", "ar"),
            ("كيف أحجز رحلة؟",
             "افتح Moviroo ← أدخل وجهتك ← اختر نوع الرحلة ← "
             "أكد موقعك ← اضغط 'طلب رحلة'.",
             "booking", "ar"),
            ("نسيت كلمة المرور، كيف أعيد تعيينها؟",
             "اضغط 'نسيت كلمة المرور' ← أدخل بريدك الإلكتروني ← "
             "افتح الرابط في الرسالة ← أنشئ كلمة مرور جديدة.",
             "password", "ar"),
            # ── Franco-Arabic ────────────────────────────────────
            ("machkel fil payement, chneya nel3ab?",
             "Verifi el flous fil carte w les détails. Ken mazal fama machkel, "
             "jrreb payment method okhra.",
             "payment", "franco-arabic"),
            ("kifech na3mal réservation?",
             "O7el Moviroo → Oktheb destination → Ikhtar type → "
             "Confirmi → Doboz 'Request Ride'.",
             "booking", "franco-arabic"),
            ("nsit el password, kifech n3awedha?",
             "Doboz 'Forgot Password' → Dakhel email → "
             "Iftah el lien fil mail → Sawwer password jdid.",
             "password", "franco-arabic"),
        ]

        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["question", "answer", "category", "language"])
            writer.writerows(sample_rows)

        logger.info(
            f"✅ dataset.csv d'exemple créé : {len(sample_rows)} entrées → {self.csv_path}"
        )

    # ──────────────────────────────────────────────────────────────
    #  Utilitaire : infos sur l'état actuel de l'index
    # ──────────────────────────────────────────────────────────────
    def get_index_status(self) -> Dict[str, Any]:
        """Retourne l'état actuel de l'index FAISS sans ré-entraîner"""
        stats = vector_store.get_stats()
        return {
            "index_loaded": vector_store.index is not None,
            "total_vectors": stats.get("total_vectors", 0),
            "by_source": stats.get("by_source", {}),
            "dimension": stats.get("dimension", 0),
            "csv_path": self.csv_path,
            "csv_exists": os.path.exists(self.csv_path),
        }

    # ──────────────────────────────────────────────────────────────
    #  Utilitaire : ajout d'un seul ticket résolu (temps-réel)
    # ──────────────────────────────────────────────────────────────
    def add_single_ticket(self, ticket_db_obj) -> bool:
        """
        Ajoute immédiatement un ticket résolu à l'index FAISS existant,
        sans reconstruction complète.

        Args:
            ticket_db_obj: objet Ticket SQLAlchemy

        Returns:
            True si ajouté, False si ignoré (doublon ou données manquantes)
        """
        q = (ticket_db_obj.question or "").strip()
        a = (ticket_db_obj.answer or "").strip()

        if not q or not a:
            logger.warning(
                f"Ticket {ticket_db_obj.ticket_id} ignoré : question ou réponse vide"
            )
            return False

        # Vérifie doublon
        fingerprint = hashlib.md5(q.lower().encode("utf-8")).hexdigest()
        for meta in vector_store.metadata:
            existing_fp = hashlib.md5(
                meta.get("question", "").lower().encode("utf-8")
            ).hexdigest()
            if existing_fp == fingerprint:
                logger.debug(
                    f"Ticket {ticket_db_obj.ticket_id} déjà indexé → ignoré"
                )
                return False

        # Encode et ajoute
        embedding = embedding_service.encode_single(q, normalize=True)
        metadata = {
            "source":    "ticket",
            "id":        ticket_db_obj.id,
            "ticket_id": ticket_db_obj.ticket_id,
            "question":  q,
            "answer":    a,
            "category":  ticket_db_obj.category or "general",
            "language":  ticket_db_obj.language or "en",
        }

        vector_store.add_vectors(np.array([embedding]), [metadata])
        vector_store.save()

        logger.info(
            f"🎫 Ticket {ticket_db_obj.ticket_id} ajouté à l'index "
            f"(total : {vector_store.index.ntotal} vecteurs)"
        )
        return True


# ──────────────────────────────────────────────────────────────────────────────
#  Instance globale
# ──────────────────────────────────────────────────────────────────────────────
training_pipeline = TrainingPipeline()
