"""
Moviroo AI Chatbot - FAISS Vector Store
Handles vector similarity search using FAISS
"""

from logging import config

import faiss
import numpy as np
import pickle
import os
from typing import List, Tuple, Optional, Dict, Any
import logging
from datetime import datetime

from config import settings
from models.embedding import embedding_service

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """
    FAISS-based vector store for semantic search
    Supports incremental updates from tickets and knowledge base
    """
    
    def __init__(self, dimension: int = None):
        """
        Initialize FAISS index
        
        Args:
            dimension: Embedding dimension (default from settings)
        """
        self.dimension = dimension or settings.embedding_dimension
        self.index = None
        self.metadata = []  # List of metadata dicts for each vector
        self.index_path = os.path.join(settings.models_dir, "faiss_index.bin")
        self.metadata_path = os.path.join(settings.models_dir, "faiss_metadata.pkl")
        
        logger.info(f"Initializing FAISS vector store (dimension={self.dimension})")
    
    def create_index(self, index_type: str = None):
        """
        Create a new FAISS index
        
        Args:
            index_type: Type of FAISS index (default from settings)
        """
        index_type = index_type or settings.faiss_index_type
        
        try:
            if index_type == "IndexFlatIP":
                # Flat index with inner product (best for normalized vectors)
                self.index = faiss.IndexFlatIP(self.dimension)
                logger.info("Created IndexFlatIP (exact search, inner product)")
            
            elif index_type == "IndexFlatL2":
                # Flat index with L2 distance
                self.index = faiss.IndexFlatL2(self.dimension)
                logger.info("Created IndexFlatL2 (exact search, L2 distance)")
            
            elif index_type == "IndexIVFFlat":
                # IVF index for faster approximate search
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
                logger.info("Created IndexIVFFlat (approximate search)")
            
            else:
                # Default to flat inner product
                self.index = faiss.IndexFlatIP(self.dimension)
                logger.info("Created default IndexFlatIP")
            
            self.metadata = []
            
        except Exception as e:
            logger.error(f"Error creating FAISS index: {e}")
            raise
    
    def add_vectors(
        self,
        embeddings: np.ndarray,
        metadata_list: List[Dict[str, Any]]
    ):
        """
        Add vectors to the index
        
        Args:
            embeddings: Numpy array of embeddings (2D)
            metadata_list: List of metadata dicts (same length as embeddings)
        """
        if self.index is None:
            self.create_index()
        
        try:
            # Ensure embeddings are 2D
            if len(embeddings.shape) == 1:
                embeddings = embeddings.reshape(1, -1)
            
            # Ensure float32 (FAISS requirement)
            embeddings = embeddings.astype('float32')
            
            # Train index if needed (for IVF)
            if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
                if len(embeddings) >= 100:
                    self.index.train(embeddings)
                    logger.info("FAISS index trained")
            
            # Add vectors to index
            self.index.add(embeddings)
            
            # Add metadata
            self.metadata.extend(metadata_list)
            
            logger.info(f"Added {len(embeddings)} vectors to FAISS index")
            logger.info(f"Total vectors in index: {self.index.ntotal}")
            
        except Exception as e:
            logger.error(f"Error adding vectors to FAISS: {e}")
            raise
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = None,
        threshold: float = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar vectors
        
        Args:
            query_embedding: Query embedding vector (1D)
            k: Number of results to return (default from settings)
            threshold: Minimum similarity threshold (default from settings)
        
        Returns:
            List of (metadata, score) tuples, sorted by score (descending)
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []
        
        k = k or settings.top_k_results
        threshold = threshold or settings.similarity_threshold
        
        try:
            # Ensure query is 2D and float32
            if len(query_embedding.shape) == 1:
                query_embedding = query_embedding.reshape(1, -1)
            query_embedding = query_embedding.astype('float32')
            
            # Search index
            k = min(k, self.index.ntotal)  # Don't request more than available
            scores, indices = self.index.search(query_embedding, k)
            
            # Flatten results (since query is single vector)
            scores = scores[0]
            indices = indices[0]
            
            # Filter by threshold and prepare results
            results = []
            for idx, score in zip(indices, scores):
                if idx >= 0 and score >= threshold:  # idx=-1 means not found
                    if idx < len(self.metadata):
                        results.append((self.metadata[idx], float(score)))
            
            logger.debug(f"Found {len(results)} results above threshold {threshold}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching FAISS index: {e}")
            return []
    
    def save(self):
        """Save FAISS index and metadata to disk"""
        try:
            if self.index is not None:
                # Save FAISS index
                faiss.write_index(self.index, self.index_path)
                
                # Save metadata
                with open(self.metadata_path, 'wb') as f:
                    pickle.dump(self.metadata, f)
                
                logger.info(f"FAISS index saved to {self.index_path}")
                logger.info(f"Metadata saved to {self.metadata_path}")
            else:
                logger.warning("No index to save")
                
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
            raise
    
    def load(self) -> bool:
        """
        Load FAISS index and metadata from disk
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
                # Load FAISS index
                self.index = faiss.read_index(self.index_path)
                
                # Load metadata
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                logger.info(f"FAISS index loaded from {self.index_path}")
                logger.info(f"Total vectors: {self.index.ntotal}")
                logger.info(f"Total metadata entries: {len(self.metadata)}")
                
                return True
            else:
                logger.warning("FAISS index files not found")
                return False
                
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            return False
    
    def update_from_ticket(self, ticket_data: Dict[str, Any]):
        """
        Add a new ticket to the index
        
        Args:
            ticket_data: Dictionary containing ticket information
        """
        try:
            # Generate embedding for question
            question = ticket_data.get('question', '')
            embedding = embedding_service.encode_single(question, normalize=True)
            
            # Prepare metadata
            metadata = {
                'source': 'ticket',
                'id': ticket_data.get('id'),
                'ticket_id': ticket_data.get('ticket_id'),
                'question': question,
                'answer': ticket_data.get('answer', ''),
                'category': ticket_data.get('category'),
                'language': ticket_data.get('language', 'en'),
                'created_at': ticket_data.get('created_at', datetime.now().isoformat()),
            }
            
            # Add to index
            self.add_vectors(
                np.array([embedding]),
                [metadata]
            )
            
            logger.info(f"Added ticket {metadata['ticket_id']} to FAISS index")
            
        except Exception as e:
            logger.error(f"Error updating index from ticket: {e}")
    
    def rebuild_index(self, all_data: List[Dict[str, Any]]):
        """
        Rebuild entire index from scratch
        
        Args:
            all_data: List of all knowledge base and ticket data
        """
        try:
            logger.info(f"Rebuilding FAISS index with {len(all_data)} items")
            
            # Create new index
            self.create_index()
            
            if not all_data:
                logger.warning("No data to rebuild index")
                return
            
            # Generate embeddings for all questions
            questions = [item['question'] for item in all_data]
            embeddings = embedding_service.encode(questions, normalize=True)
            
            # Prepare metadata
            metadata_list = []
            for item in all_data:
                metadata = {
                    'source': item.get('source', 'knowledge_base'),
                    'id': item.get('id'),
                    'question': item.get('question'),
                    'answer': item.get('answer'),
                    'category': item.get('category'),
                    'language': item.get('language', 'en'),
                }
                metadata_list.append(metadata)
            
            # Add all vectors
            self.add_vectors(embeddings, metadata_list)
            
            # Save index
            self.save()
            
            logger.info("FAISS index rebuilt successfully")
            
        except Exception as e:
            logger.error(f"Error rebuilding FAISS index: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        if self.index is None:
            return {
                'total_vectors': 0,
                'dimension': self.dimension,
                'is_trained': False,
            }
        
        stats = {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'is_trained': getattr(self.index, 'is_trained', True),
            'metadata_count': len(self.metadata),
        }
        
        # Count by source
        source_counts = {}
        for meta in self.metadata:
            source = meta.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        stats['by_source'] = source_counts
        
        return stats
if __name__ == "__main__":
    print("FAISS Vector Store test mode")
    vector_store = FAISSVectorStore()

    from models.embedding import embedding_service

    embedding_service.load_model()

    vec = embedding_service.encode_single("hello world")
    print("Embedding shape:", vec.shape)

    store = FAISSVectorStore()
    store.create_index()

    store.add_vectors(
        np.array([vec]),
        [{
            "source": "test",
            "question": "hello world",
            "answer": "test answer",
            "category": "test"
        }]
    )

    print("Vectors in index:", store.index.ntotal)

    results = store.search(vec, k=1)
    print("Search results:", results)