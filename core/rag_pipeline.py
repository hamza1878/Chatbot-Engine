"""
Moviroo AI Chatbot - RAG Pipeline
FAISS retrieval → score routing → LLM generation
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging

from models.embedding import embedding_service
from models.vector_store import FAISSVectorStore
from core.llm_service import generate_answer
from config import settings

logger = logging.getLogger(__name__)

# ── Language-switch commands (not real support questions) ────────
LANGUAGE_COMMANDS = [
    "en français", "en francais", "in english", "in french",
    "بالعربية", "بالعربي", "en arabe", "in arabic",
    "franco", "franco-arabe", "بالفرنسية",
]

# ── Greeting detection ───────────────────────────────────────────
GREETINGS = [
    "hello", "hi", "hey", "bonjour", "salut", "salam", "ahla",
    "مرحبا", "أهلا", "السلام عليكم", "wesh", "wa3lik",
]


@dataclass
class RAGResponse:
    answer: str
    confidence: float
    category: str
    language: str
    source: str          # direct_match | rag_llm | fallback
    suggest_ticket: bool
    top_chunks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "category": self.category,
            "language": self.language,
            "source": self.source,
            "suggest_ticket": self.suggest_ticket,
        }


class RAGPipeline:
    """
    3-tier routing:
      score >= HIGH  → direct answer from best chunk (fast, no LLM)
      score >= LOW   → LLM generates enriched answer using top-k context
      score <  LOW   → fallback, suggest ticket

    Pre-routing:
      language commands → polite language acknowledgement
      greetings         → welcome message
    """

    def __init__(self, vector_store: Optional[FAISSVectorStore] = None):
        self.vector_store = vector_store
        self.HIGH = settings.high_confidence_threshold  # default 0.82
        self.LOW = settings.low_confidence_threshold    # default 0.55

    def set_vector_store(self, vs: FAISSVectorStore):
        self.vector_store = vs

    async def run(self, question: str) -> RAGResponse:
        q = question.strip()

        if not q:
            return self._fallback("Question vide.")

        if self.vector_store is None:
            logger.error("RAG pipeline: vector store not set")
            return self._fallback("Service temporairement indisponible.")

        q_lower = q.lower()

        # ── Pre-routing: language command ────────────────────────
        if any(cmd in q_lower for cmd in LANGUAGE_COMMANDS):
            return RAGResponse(
                answer=(
                    "Bien sûr ! Je parle français, English, العربية et le franco-arabe. "
                    "Posez votre question dans la langue de votre choix et je vous répondrai."
                ),
                confidence=1.0,
                category="general",
                language="fr",
                source="direct_match",
                suggest_ticket=False,
            )

        # ── Pre-routing: greeting ────────────────────────────────
        if any(q_lower == g or q_lower.startswith(g + " ") for g in GREETINGS):
            return RAGResponse(
                answer=(
                    "Hello! 👋 I'm the Moviroo support assistant. "
                    "How can I help you today? You can ask in English, Français, العربية or Franco-Arabic."
                ),
                confidence=1.0,
                category="general",
                language="en",
                source="direct_match",
                suggest_ticket=False,
            )

        # ── 1. Embed question ────────────────────────────────────
        try:
            query_vec = embedding_service.encode_single(q, normalize=True)
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return self._fallback("Erreur technique.")

        # ── 2. FAISS retrieval ───────────────────────────────────
        results = self.vector_store.search(query_vec, k=5, threshold=self.LOW)
        logger.info(f"FAISS: {len(results)} results for '{q[:60]}'")

        if not results:
            return self._fallback(
                "Je n'ai pas trouvé de réponse correspondante. "
                "Un agent va vous contacter."
            )

        best_meta, best_score = results[0]
        chunks = [m for m, _ in results]

        # ── 3. Routing by confidence score ───────────────────────
        if best_score >= self.HIGH:
            # Fast path: answer directly from CSV/knowledge base
            return RAGResponse(
                answer=best_meta["answer"],
                confidence=round(best_score, 3),
                category=best_meta.get("category", "general"),
                language=best_meta.get("language", "en"),
                source="direct_match",
                suggest_ticket=False,
                top_chunks=chunks,
            )

        # Medium confidence: LLM reformulates using top-k context
        llm_answer = await generate_answer(q, chunks)

        return RAGResponse(
            answer=llm_answer,
            confidence=round(best_score, 3),
            category=best_meta.get("category", "general"),
            language=best_meta.get("language", "en"),
            source="rag_llm",
            suggest_ticket=best_score < self.LOW + 0.1,
            top_chunks=chunks,
        )

    @staticmethod
    def _fallback(msg: str) -> RAGResponse:
        return RAGResponse(
            answer=msg,
            confidence=0.0,
            category="unknown",
            language="fr",
            source="fallback",
            suggest_ticket=True,
        )


rag_pipeline = RAGPipeline()