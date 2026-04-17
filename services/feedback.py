"""
Moviroo AI Chatbot - Feedback Service
Handles user feedback collection and processing for continuous improvement
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from datetime import datetime, timedelta
import logging

from database.models import Feedback, ConversationMessage, Ticket
from config import settings
from models.vector_store import FAISSVectorStore
logger = logging.getLogger(__name__)
vector_store = FAISSVectorStore()

class FeedbackService:
    """Service for collecting and processing user feedback"""
    
    async def submit_feedback(
        self,
        db: AsyncSession,
        conversation_id: str,
        rating: int,
        feedback_type: str,
        user_message: str,
        bot_response: str,
        comment: Optional[str] = None,
        message_id: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Feedback:
        """
        Submit user feedback
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            rating: Rating (1-5)
            feedback_type: Type of feedback
            user_message: Original user message
            bot_response: Bot's response
            comment: Optional user comment
            message_id: Optional message ID
            user_id: Optional user ID
        
        Returns:
            Created feedback
        """
        try:
            # Validate rating
            if not 1 <= rating <= 5:
                raise ValueError("Rating must be between 1 and 5")
            
            # Create feedback
            feedback = Feedback(
                conversation_id=conversation_id,
                message_id=message_id,
                rating=rating,
                feedback_type=feedback_type,
                user_message=user_message,
                bot_response=bot_response,
                comment=comment,
                user_id=user_id,
                is_processed=False
            )
            
            db.add(feedback)
            await db.commit()
            await db.refresh(feedback)
            
            logger.info(f"Feedback submitted: rating={rating}, type={feedback_type}")
            
            # Process high-quality feedback immediately
            if rating >= settings.feedback_threshold and settings.auto_learning_enabled:
                await self._process_positive_feedback(db, feedback)
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            await db.rollback()
            raise
    
    async def _process_positive_feedback(
        self,
        db: AsyncSession,
        feedback: Feedback
    ):
        """
        Process positive feedback for learning
        
        Args:
            db: Database session
            feedback: Feedback to process
        """
        try:
            # Mark as processed
            feedback.is_processed = True
            feedback.processed_at = datetime.now()
            
            await db.commit()
            
            logger.info(f"Processed positive feedback {feedback.id}")
            
            # TODO: Could trigger re-training or index update here
            
        except Exception as e:
            logger.error(f"Error processing positive feedback: {e}")
    
    async def get_feedback_stats(
        self,
        db: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get feedback statistics
        
        Args:
            db: Database session
            days: Number of days to analyze
        
        Returns:
            Statistics dictionary
        """
        try:
            # Date range
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Total feedback
            total_result = await db.execute(
                select(Feedback).where(Feedback.created_at >= cutoff_date)
            )
            all_feedback = list(total_result.scalars().all())
            total_count = len(all_feedback)
            
            if total_count == 0:
                return {
                    'total_feedback': 0,
                    'average_rating': 0.0,
                    'by_rating': {},
                    'by_type': {},
                    'processed_count': 0,
                }
            
            # Average rating
            avg_rating = sum(f.rating for f in all_feedback) / total_count
            
            # By rating
            rating_counts = {}
            for rating in range(1, 6):
                count = sum(1 for f in all_feedback if f.rating == rating)
                rating_counts[rating] = count
            
            # By type
            type_counts = {}
            for feedback in all_feedback:
                type_counts[feedback.feedback_type] = type_counts.get(feedback.feedback_type, 0) + 1
            
            # Processed count
            processed_count = sum(1 for f in all_feedback if f.is_processed)
            
            return {
                'total_feedback': total_count,
                'average_rating': round(avg_rating, 2),
                'by_rating': rating_counts,
                'by_type': type_counts,
                'processed_count': processed_count,
                'processing_rate': round(processed_count / total_count * 100, 2) if total_count > 0 else 0,
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return {}
    
    async def get_low_rated_feedback(
        self,
        db: AsyncSession,
        max_rating: int = 2,
        limit: int = 20
    ) -> List[Feedback]:
        """
        Get low-rated feedback for analysis
        
        Args:
            db: Database session
            max_rating: Maximum rating to include
            limit: Maximum number of results
        
        Returns:
            List of low-rated feedback
        """
        try:
            result = await db.execute(
                select(Feedback)
                .where(Feedback.rating <= max_rating)
                .order_by(desc(Feedback.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting low-rated feedback: {e}")
            return []
    
    async def get_unprocessed_feedback(
        self,
        db: AsyncSession,
        limit: int = 50
    ) -> List[Feedback]:
        """
        Get unprocessed feedback
        
        Args:
            db: Database session
            limit: Maximum number of results
        
        Returns:
            List of unprocessed feedback
        """
        try:
            result = await db.execute(
                select(Feedback)
                .where(Feedback.is_processed == False)
                .order_by(desc(Feedback.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting unprocessed feedback: {e}")
            return []
    
    async def mark_processed(
        self,
        db: AsyncSession,
        feedback_ids: List[int]
    ) -> int:
        """
        Mark feedback as processed
        
        Args:
            db: Database session
            feedback_ids: List of feedback IDs
        
        Returns:
            Number of updated records
        """
        try:
            result = await db.execute(
                select(Feedback).where(Feedback.id.in_(feedback_ids))
            )
            feedbacks = list(result.scalars().all())
            
            for feedback in feedbacks:
                feedback.is_processed = True
                feedback.processed_at = datetime.now()
            
            await db.commit()
            
            logger.info(f"Marked {len(feedbacks)} feedback as processed")
            return len(feedbacks)
            
        except Exception as e:
            logger.error(f"Error marking feedback as processed: {e}")
            await db.rollback()
            return 0
    
    async def analyze_improvement_opportunities(
        self,
        db: AsyncSession,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze feedback to find improvement opportunities
        
        Args:
            db: Database session
            days: Number of days to analyze
        
        Returns:
            Analysis results
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get low-rated feedback
            result = await db.execute(
                select(Feedback)
                .where(
                    and_(
                        Feedback.rating <= 2,
                        Feedback.created_at >= cutoff_date
                    )
                )
            )
            low_rated = list(result.scalars().all())
            
            # Common issues
            issue_keywords = {
                'payment': ['payment', 'pay', 'charge', 'credit', 'debit', 'refund'],
                'delay': ['late', 'delay', 'waiting', 'slow', 'stuck'],
                'booking': ['book', 'reserve', 'cancel', 'trip'],
                'account': ['account', 'login', 'password', 'profile'],
                'bug': ['bug', 'error', 'crash', 'broken', 'not working'],
            }
            
            issue_counts = {issue: 0 for issue in issue_keywords}
            
            for feedback in low_rated:
                message = (feedback.user_message + ' ' + feedback.bot_response).lower()
                for issue, keywords in issue_keywords.items():
                    if any(keyword in message for keyword in keywords):
                        issue_counts[issue] += 1
            
            # Sort by frequency
            top_issues = sorted(
                issue_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return {
                'total_low_rated': len(low_rated),
                'analysis_period_days': days,
                'top_issues': [
                    {'issue': issue, 'count': count}
                    for issue, count in top_issues if count > 0
                ],
                'needs_attention': len(low_rated) > 10,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing improvement opportunities: {e}")
            return {}


# Global feedback service instance
feedback_service = FeedbackService()
