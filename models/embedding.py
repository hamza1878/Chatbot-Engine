"""
Moviroo AI Chatbot - Embedding Service
Handles text embeddings using SentenceTransformers for multilingual support
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import logging
import torch

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating multilingual embeddings
    Supports: English, French, Arabic, Franco-Arabic
    """
    
    def __init__(self):
        """Initialize the multilingual embedding model"""
        self.model_name = settings.embedding_model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.dimension = settings.embedding_dimension
        
        logger.info(f"Initializing embedding model: {self.model_name}")
        logger.info(f"Using device: {self.device}")
    
    def load_model(self):
        """Load the SentenceTransformer model"""
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Embedding model loaded successfully on {self.device}")
            logger.info(f"Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text before embedding
        Handles Franco-Arabic and special characters
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Handle common Franco-Arabic patterns
        franco_mappings = {
            "machkel": "مشكل problem",
            "fil": "في in",
            "mafihch": "ما فيش no",
            "barcha": "برشا many",
            "yesser": "ياسر very",
            "chkoun": "شكون who",
            "kifech": "كيفاش how",
            "wakt": "وقت time",
            "flous": "فلوس money",
        }
        
        # Augment Franco-Arabic with translations
        text_lower = text.lower()
        for franco, translation in franco_mappings.items():
            if franco in text_lower:
                text = f"{text} {translation}"
        
        return text
    
    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Generate embeddings for one or more texts
        
        Args:
            texts: Single text or list of texts
            normalize: Whether to normalize embeddings (for cosine similarity)
        
        Returns:
            Numpy array of embeddings
        """
        if self.model is None:
            self.load_model()
        
        # Handle single text
        if isinstance(texts, str):
            texts = [texts]
        
        # Preprocess all texts
        texts = [self.preprocess_text(text) for text in texts]
        
        try:
            # Generate embeddings
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=normalize,
                show_progress_bar=False,
                convert_to_numpy=True,
                batch_size=32
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
            normalize: Whether to normalize embedding
        
        Returns:
            1D numpy array of embedding
        """
        embeddings = self.encode([text], normalize=normalize)
        return embeddings[0]
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
        
        Returns:
            Similarity score between -1 and 1
        """
        # Ensure embeddings are normalized
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Calculate cosine similarity (dot product of normalized vectors)
        similarity = np.dot(embedding1, embedding2)
        
        return float(similarity)
    
    def batch_similarity(
        self,
        query_embedding: np.ndarray,
        embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calculate similarity between one query and multiple embeddings
        
        Args:
            query_embedding: Query embedding vector (1D)
            embeddings: Multiple embeddings (2D array)
        
        Returns:
            Array of similarity scores
        """
        # Normalize query
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Normalize all embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized_embeddings = embeddings / norms
        
        # Calculate similarities (dot product)
        similarities = np.dot(normalized_embeddings, query_embedding)
        
        return similarities
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        if self.model is None:
            return self.dimension
        return self.model.get_sentence_embedding_dimension()


# Global embedding service instance
embedding_service = EmbeddingService()
