"""
Moviroo AI Chatbot - FAISS Vector Store
"""
import faiss
import numpy as np
import pickle
import os
from typing import List, Tuple, Optional, Dict, Any
import logging
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """
    FAISS-based semantic search.
    IndexFlatIP (inner product) on normalized vectors = cosine similarity.
    """

    def __init__(self, dimension: int = None):
        self.dimension = dimension or settings.embedding_dimension
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []
        self.index_path = os.path.join(settings.models_dir, "faiss_index.bin")
        self.metadata_path = os.path.join(settings.models_dir, "faiss_metadata.pkl")

    # ── Index management ────────────────────────────────────────────────

    def create_index(self):
        index_type = settings.faiss_index_type
        if index_type == "IndexFlatIP":
            self.index = faiss.IndexFlatIP(self.dimension)
        elif index_type == "IndexFlatL2":
            self.index = faiss.IndexFlatL2(self.dimension)
        elif index_type == "IndexIVFFlat":
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        logger.info(f"FAISS index created: {index_type}")

    def add_vectors(self, embeddings: np.ndarray, metadata_list: List[Dict[str, Any]]):
        if self.index is None:
            self.create_index()
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        embeddings = embeddings.astype("float32")

        # Train IVF if needed
        if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
            if len(embeddings) >= 100:
                self.index.train(embeddings)

        self.index.add(embeddings)
        self.metadata.extend(metadata_list)
        logger.debug(f"Added {len(embeddings)} vectors — total={self.index.ntotal}")

    # ── Search ──────────────────────────────────────────────────────────

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = None,
        threshold: float = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        if self.index is None or self.index.ntotal == 0:
            return []

        k = min(k or settings.top_k_results, self.index.ntotal)
        threshold = threshold if threshold is not None else settings.similarity_threshold

        query = query_embedding.reshape(1, -1).astype("float32")
        scores, indices = self.index.search(query, k)

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx >= 0 and score >= threshold and idx < len(self.metadata):
                results.append((self.metadata[idx], float(score)))

        return results

    # ── Persistence ─────────────────────────────────────────────────────

    def save(self):
        if self.index is None:
            logger.warning("Nothing to save")
            return
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)
        logger.info(f"Saved {self.index.ntotal} vectors")

    def load(self) -> bool:
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.metadata_path, "rb") as f:
                self.metadata = pickle.load(f)
            logger.info(f"Loaded {self.index.ntotal} vectors from disk")
            return True
        return False

    # ── Incremental update ───────────────────────────────────────────────

    def add_ticket(self, ticket, embedding_service):
        """Add a single resolved ticket to the index."""
        q = getattr(ticket, "question", "") or ""
        a = getattr(ticket, "answer", "") or ""
        if not q or not a:
            return False
        vec = embedding_service.encode_single(q, normalize=True)
        meta = {
            "source": "ticket",
            "id": ticket.id,
            "ticket_id": ticket.ticket_id,
            "question": q,
            "answer": a,
            "category": getattr(ticket, "category", None),
            "language": getattr(ticket, "language", "en"),
            "created_at": datetime.now().isoformat(),
        }
        self.add_vectors(np.array([vec]), [meta])
        return True

    def rebuild(self, all_data: List[Dict[str, Any]], embedding_service):
        """Full rebuild from list of dicts with 'question', 'answer', etc."""
        self.create_index()
        if not all_data:
            return
        questions = [d["question"] for d in all_data]
        embeddings = embedding_service.encode(questions, normalize=True)
        metadata_list = [
            {
                "source": d.get("source", "knowledge_base"),
                "id": d.get("id"),
                "question": d.get("question"),
                "answer": d.get("answer"),
                "category": d.get("category"),
                "language": d.get("language", "en"),
            }
            for d in all_data
        ]
        self.add_vectors(embeddings, metadata_list)
        self.save()
        logger.info(f"Index rebuilt: {self.index.ntotal} vectors")

    # ── Stats ────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        if self.index is None:
            return {"total_vectors": 0, "dimension": self.dimension}
        sources: Dict[str, int] = {}
        cats: Dict[str, int] = {}
        for m in self.metadata:
            sources[m.get("source", "?")] = sources.get(m.get("source", "?"), 0) + 1
            cats[m.get("category", "?")] = cats.get(m.get("category", "?"), 0) + 1
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "by_source": sources,
            "by_category": cats,
        }


vector_store = FAISSVectorStore()
