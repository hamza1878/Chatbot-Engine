"""
Moviroo AI Chatbot - Chatbot Service
Main chatbot logic for processing user messages and generating responses
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import uuid
import json

from models.embedding import embedding_service
from models.vector_store import FAISSVectorStore
from config import settings

logger = logging.getLogger(__name__)
vector_store = FAISSVectorStore()

class ChatbotService:
    """
    Main chatbot service for processing user queries
    Handles multilingual understanding and semantic search
    """
    
    def __init__(self):
        """Initialize chatbot service"""
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.fallback_responses = self._load_fallback_responses()
        
        logger.info("ChatbotService initialized")
    
    def _load_fallback_responses(self) -> Dict[str, List[str]]:
        """Load fallback responses for different languages"""
        return {
            'en': [
                "I'm not quite sure about that. Could you please rephrase your question?",
                "I couldn't find a specific answer to your question. Would you like to create a support ticket?",
                "I'm still learning! Let me connect you with our support team who can help better.",
                "I don't have enough information to answer that accurately. Can you provide more details?",
            ],
            'fr': [
                "Je ne suis pas sûr de comprendre. Pourriez-vous reformuler votre question ?",
                "Je n'ai pas trouvé de réponse spécifique. Voulez-vous créer un ticket de support ?",
                "Je suis encore en apprentissage ! Laissez-moi vous connecter avec notre équipe de support.",
                "Je n'ai pas assez d'informations pour répondre précisément. Pouvez-vous donner plus de détails ?",
            ],
            'ar': [
                "لست متأكدًا من فهمي. هل يمكنك إعادة صياغة سؤالك؟",
                "لم أجد إجابة محددة لسؤالك. هل تريد إنشاء تذكرة دعم؟",
                "ما زلت أتعلم! دعني أوصلك بفريق الدعم.",
                "ليس لدي معلومات كافية للإجابة بدقة. هل يمكنك تقديم المزيد من التفاصيل؟",
            ],
            'franco-arabic': [
                "Mafahamtech behi. Tnajam t3awed teshra7 sou2alek?",
                "Mal9itch jaweb moutabeg. T7eb ta3mal ticket support?",
                "Mazelt net3alem! Bech nwaslek bl équipe mte3 support.",
                "Ma3andich barcha info bech njaweb b précision. Tnajam tziid détails?",
            ]
        }
    
    def detect_language(self, text: str) -> str:
        """
        Detect language from text
        
        Args:
            text: Input text
        
        Returns:
            Language code: 'en', 'fr', 'ar', 'franco-arabic'
        """
        # Simple heuristic-based language detection
        text_lower = text.lower()
        
        # Check for Arabic characters
        if any('\u0600' <= c <= '\u06FF' for c in text):
            return 'ar'
        
        # Check for Franco-Arabic keywords
        franco_keywords = [
            'machkel', 'fil', 'mafihch', 'barcha', 'yesser',
            'chkoun', 'kifech', 'wakt', 'flous', 'behi',
            'taw', 'mouch', 'chbik', 'tnajam', 'bech'
        ]
        if any(keyword in text_lower for keyword in franco_keywords):
            return 'franco-arabic'
        
        # Check for French keywords
        french_keywords = [
            'bonjour', 'merci', 'problème', 'comment', 'pourquoi',
            'voudrais', 'besoin', 'aide', 'svp', 'stp'
        ]
        if any(keyword in text_lower for keyword in french_keywords):
            return 'fr'
        
        # Default to English
        return 'en'
    
    def detect_category(self, text: str) -> Optional[str]:
        """
        Detect query category from text
        
        Args:
            text: Input text
        
        Returns:
            Category name or None
        """
        text_lower = text.lower()
        
        # Category keywords (multilingual)
        category_keywords = {
            'payment': [
                'payment', 'pay', 'credit card', 'debit', 'money', 'charge', 'refund',
                'paiement', 'payer', 'carte', 'argent', 'remboursement',
                'دفع', 'مال', 'بطاقة', 'استرجاع',
                'flous', 'khlass', 'carte bancaire'
            ],
            'ride_delay': [
                'late', 'delay', 'waiting', 'time', 'slow', 'stuck',
                'retard', 'attente', 'lent',
                'تأخير', 'انتظار', 'بطيء',
                'ta5ir', 'estanna', 'bti2'
            ],
            'booking': [
                'book', 'reserve', 'ride', 'trip', 'cancel', 'modify',
                'réserver', 'voyage', 'annuler', 'modifier',
                'حجز', 'رحلة', 'إلغاء',
                'reservation', '7ajz', 'voyage'
            ],
            'account': [
                'account', 'profile', 'login', 'sign up', 'register',
                'compte', 'profil', 'connexion', 'inscription',
                'حساب', 'تسجيل', 'دخول',
                'compte', 'connexion', 'inscrit'
            ],
            'password': [
                'password', 'reset', 'forgot', 'change password',
                'mot de passe', 'réinitialiser', 'oublié',
                'كلمة المرور', 'نسيت', 'إعادة تعيين',
                'mot de passe', 'nsit', 'reset'
            ],
            'bug': [
                'bug', 'error', 'crash', 'not working', 'broken', 'issue',
                'erreur', 'problème', 'ne marche pas', 'cassé',
                'خطأ', 'مشكلة', 'لا يعمل',
                'machkel', 'ma5demnech', 'erreur'
            ]
        }
        
        # Count keyword matches for each category
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return None
    
    async def process_message(
        self,
        user_message: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user message and generate response
        
        Args:
            user_message: User's input message
            user_id: Optional user ID
            conversation_id: Optional conversation ID
        
        Returns:
            Dictionary with response and metadata
        """
        start_time = datetime.now()
        
        try:
            # Detect language and category
            detected_language = self.detect_language(user_message)
            detected_category = self.detect_category(user_message)
            
            logger.info(f"Processing message (lang={detected_language}, cat={detected_category})")
            logger.debug(f"User message: {user_message[:100]}")
            
            # Generate embedding for user message
            query_embedding = self.embedding_service.encode_single(
                user_message,
                normalize=True
            )
            
            # Search in vector store
            search_results = self.vector_store.search(
                query_embedding,
                k=settings.top_k_results,
                threshold=settings.similarity_threshold
            )
            
            # Process search results
            if search_results:
                # Get best match
                best_match, best_score = search_results[0]
                
                response_text = best_match['answer']
                matched_source = best_match['source']
                matched_id = best_match.get('id')
                
                logger.info(f"Found match: score={best_score:.3f}, source={matched_source}")
                
            else:
                # No good match found - use fallback
                response_text = self._get_fallback_response(detected_language)
                best_score = 0.0
                matched_source = 'fallback'
                matched_id = None
                
                logger.warning("No good match found, using fallback response")
            
            # Calculate response time
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Prepare response
            response = {
                'response': response_text,
                'confidence_score': float(best_score),
                'detected_language': detected_language,
                'detected_category': detected_category,
                'matched_source': matched_source,
                'matched_id': matched_id,
                'response_time_ms': response_time_ms,
                'conversation_id': conversation_id or str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
            }
            
            # Add suggestions if confidence is low
            if best_score < settings.min_confidence_score:
                response['suggestions'] = [
                    "Try rephrasing your question",
                    "Provide more specific details",
                    "Create a support ticket for personalized help"
                ]
            
            # Add alternative answers if available
            if len(search_results) > 1:
                response['alternatives'] = [
                    {
                        'answer': match['answer'],
                        'score': float(score),
                        'category': match.get('category')
                    }
                    for match, score in search_results[1:3]  # Top 2 alternatives
                ]
            
            logger.info(f"Response generated in {response_time_ms}ms")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            # Return error response
            return {
                'response': "I apologize, but I encountered an error processing your message. Please try again or contact support.",
                'confidence_score': 0.0,
                'detected_language': 'en',
                'detected_category': None,
                'matched_source': 'error',
                'matched_id': None,
                'response_time_ms': 0,
                'conversation_id': conversation_id or str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _get_fallback_response(self, language: str) -> str:
        """
        Get fallback response in appropriate language
        
        Args:
            language: Detected language code
        
        Returns:
            Fallback response text
        """
        import random
        
        responses = self.fallback_responses.get(language, self.fallback_responses['en'])
        return random.choice(responses)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chatbot statistics"""
        vector_stats = self.vector_store.get_stats()
        
        return {
            'vector_store': vector_stats,
            'embedding_model': self.embedding_service.model_name,
            'embedding_dimension': self.embedding_service.get_dimension(),
            'supported_languages': settings.supported_languages_list,
            'similarity_threshold': settings.similarity_threshold,
        }


# Global chatbot service instance
chatbot_service = ChatbotService()
