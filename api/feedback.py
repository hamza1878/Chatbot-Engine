"""
Moviroo AI Chatbot - Feedback API Routes
FastAPI endpoints for user feedback and continuous improvement
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from api.schemas import FeedbackRequest, FeedbackResponse
from database.connection import get_db_session
from services.feedback import feedback_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Submit user feedback on chatbot response
    
    - **conversation_id**: Conversation identifier (required)
    - **rating**: Rating from 1-5 stars (required)
    - **feedback_type**: Type of feedback (required)
        - helpful: Response was helpful
        - not_helpful: Response was not helpful
        - wrong_answer: Incorrect information
        - incomplete_answer: Missing information
        - good_response: Excellent response
        - needs_improvement: Could be better
    - **user_message**: Original user message (required)
    - **bot_response**: Bot's response (required)
    - **comment**: Optional additional comments (max 500 chars)
    - **message_id**: Optional message ID for linking
    - **user_id**: Optional user identifier
    
    Returns:
    - Confirmation with feedback ID
    
    Note: High-rated feedback (4-5 stars) is automatically processed
    for continuous learning when auto_learning is enabled.
    """
    try:
        feedback = await feedback_service.submit_feedback(
            db=db,
            conversation_id=request.conversation_id,
            rating=request.rating,
            feedback_type=request.feedback_type,
            user_message=request.user_message,
            bot_response=request.bot_response,
            comment=request.comment,
            message_id=request.message_id,
            user_id=request.user_id
        )
        
        logger.info(
            f"Feedback submitted: rating={request.rating}, "
            f"type={request.feedback_type}, conversation={request.conversation_id}"
        )
        
        return feedback
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_feedback_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get feedback statistics (admin only)
    
    - **days**: Number of days to analyze (1-365, default: 30)
    
    Returns:
    - Total feedback count
    - Average rating
    - Rating distribution (1-5 stars)
    - Feedback type distribution
    - Processing metrics
    """
    try:
        stats = await feedback_service.get_feedback_stats(db, days=days)
        return stats
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/low-rated", status_code=status.HTTP_200_OK)
async def get_low_rated_feedback(
    max_rating: int = Query(default=2, ge=1, le=5),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get low-rated feedback for analysis (admin only)
    
    - **max_rating**: Maximum rating to include (1-5, default: 2)
    - **limit**: Maximum number of results (1-100, default: 20)
    
    Returns:
    - List of low-rated feedback entries with user comments
    """
    try:
        feedbacks = await feedback_service.get_low_rated_feedback(
            db=db,
            max_rating=max_rating,
            limit=limit
        )
        
        return [
            {
                'id': f.id,
                'conversation_id': f.conversation_id,
                'rating': f.rating,
                'feedback_type': f.feedback_type,
                'user_message': f.user_message,
                'bot_response': f.bot_response,
                'comment': f.comment,
                'created_at': f.created_at.isoformat()
            }
            for f in feedbacks
        ]
        
    except Exception as e:
        logger.error(f"Error getting low-rated feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/unprocessed", status_code=status.HTTP_200_OK)
async def get_unprocessed_feedback(
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get unprocessed feedback (admin only)
    
    - **limit**: Maximum number of results (1-100, default: 50)
    
    Returns:
    - List of feedback that hasn't been processed yet
    """
    try:
        feedbacks = await feedback_service.get_unprocessed_feedback(
            db=db,
            limit=limit
        )
        
        return [
            {
                'id': f.id,
                'conversation_id': f.conversation_id,
                'rating': f.rating,
                'feedback_type': f.feedback_type,
                'comment': f.comment,
                'created_at': f.created_at.isoformat()
            }
            for f in feedbacks
        ]
        
    except Exception as e:
        logger.error(f"Error getting unprocessed feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/process", status_code=status.HTTP_200_OK)
async def process_feedback(
    feedback_ids: List[int],
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mark feedback as processed (admin only)
    
    - **feedback_ids**: List of feedback IDs to mark as processed
    
    Returns:
    - Number of feedback entries processed
    """
    try:
        count = await feedback_service.mark_processed(db, feedback_ids)
        
        return {
            'message': f'Processed {count} feedback entries',
            'count': count
        }
        
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/analysis/improvements", status_code=status.HTTP_200_OK)
async def analyze_improvements(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Analyze feedback to identify improvement opportunities (admin only)
    
    - **days**: Number of days to analyze (1-30, default: 7)
    
    Returns:
    - Total low-rated feedback count
    - Top issues identified from feedback
    - Whether immediate attention is needed
    """
    try:
        analysis = await feedback_service.analyze_improvement_opportunities(
            db=db,
            days=days
        )
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing improvements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
