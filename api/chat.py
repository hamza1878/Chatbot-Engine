"""
Moviroo AI Chatbot - Chat API Routes
FastAPI endpoints for chat functionality
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging
import uuid

from api.schemas import ChatRequest, ChatResponse
from database.connection import get_db_session
from database.models import Conversation, ConversationMessage
from services.chatbot import chatbot_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Process user message and generate AI response
    
    - **message**: User's question or message (required, 1-1000 characters)
    - **user_id**: Optional user identifier for tracking
    - **conversation_id**: Optional conversation ID to continue existing conversation
    - **language**: Optional language hint (auto-detected if not provided)
    
    Returns:
    - AI response with confidence score and metadata
    - Detected language and category
    - Response time and conversation ID
    """
    try:
        start_time = datetime.now()
        
        # Generate or use existing conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Get or create conversation
        conversation = None
        if request.user_id:
            # Check if conversation exists
            from sqlalchemy import select
            result = await db.execute(
                select(Conversation).where(
                    Conversation.conversation_id == conversation_id
                )
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                # Create new conversation
                conversation = Conversation(
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    is_active=True
                )
                db.add(conversation)
                await db.flush()
        
        # Process message through chatbot service
        response_data = await chatbot_service.process_message(
            user_message=request.message,
            user_id=request.user_id,
            conversation_id=conversation_id
        )
        
        # Save conversation message
        if conversation:
            message = ConversationMessage(
                conversation_id=conversation_id,
                user_message=request.message,
                bot_response=response_data['response'],
                detected_language=response_data['detected_language'],
                detected_category=response_data['detected_category'],
                confidence_score=response_data['confidence_score'],
                matched_source=response_data['matched_source'],
                matched_id=response_data['matched_id'],
                response_time_ms=response_data['response_time_ms']
            )
            db.add(message)
            
            # Update conversation stats
            conversation.total_messages += 1
            if conversation.avg_confidence == 0:
                conversation.avg_confidence = response_data['confidence_score']
            else:
                # Running average
                conversation.avg_confidence = (
                    conversation.avg_confidence * (conversation.total_messages - 1) +
                    response_data['confidence_score']
                ) / conversation.total_messages
            
            await db.commit()
        
        logger.info(
            f"Chat processed: user={request.user_id}, "
            f"confidence={response_data['confidence_score']:.2f}, "
            f"time={response_data['response_time_ms']}ms"
        )
        
        return ChatResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/history/{conversation_id}", status_code=status.HTTP_200_OK)
async def get_conversation_history(
    conversation_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get conversation history
    
    - **conversation_id**: Conversation identifier
    - **limit**: Maximum number of messages to return (default: 20)
    
    Returns:
    - List of conversation messages with timestamps
    """
    try:
        from sqlalchemy import select, desc
        
        # Get conversation
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.conversation_id == conversation_id
            )
        )
        conversation = conv_result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Get messages
        msg_result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(desc(ConversationMessage.created_at))
            .limit(limit)
        )
        messages = list(msg_result.scalars().all())
        
        # Reverse to get chronological order
        messages.reverse()
        
        return {
            'conversation_id': conversation_id,
            'user_id': conversation.user_id,
            'total_messages': conversation.total_messages,
            'avg_confidence': conversation.avg_confidence,
            'messages': [
                {
                    'user_message': msg.user_message,
                    'bot_response': msg.bot_response,
                    'confidence_score': msg.confidence_score,
                    'detected_language': msg.detected_language,
                    'detected_category': msg.detected_category,
                    'timestamp': msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/conversation/{conversation_id}", status_code=status.HTTP_200_OK)
async def end_conversation(
    conversation_id: str,
    user_satisfaction: int = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    End a conversation and optionally provide satisfaction rating
    
    - **conversation_id**: Conversation identifier
    - **user_satisfaction**: Optional satisfaction rating (1-5)
    
    Returns:
    - Confirmation message
    """
    try:
        from sqlalchemy import select
        
        result = await db.execute(
            select(Conversation).where(
                Conversation.conversation_id == conversation_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        conversation.is_active = False
        conversation.ended_at = datetime.now()
        
        if user_satisfaction is not None:
            if 1 <= user_satisfaction <= 5:
                conversation.user_satisfaction = user_satisfaction
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Satisfaction rating must be between 1 and 5"
                )
        
        await db.commit()
        
        return {
            'message': 'Conversation ended successfully',
            'conversation_id': conversation_id,
            'total_messages': conversation.total_messages,
            'avg_confidence': conversation.avg_confidence
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
