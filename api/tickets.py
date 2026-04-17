"""
Moviroo AI Chatbot - Ticket API Routes
FastAPI endpoints for support ticket management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from api.schemas import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketResponse
)
from database.connection import get_db_session
from services.ticket import ticket_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ticket", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    request: TicketCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new support ticket
    
    - **user_id**: User identifier (required)
    - **question**: User's question or issue description (required, min 10 chars)
    - **category**: Optional category classification
    - **language**: Language code (default: 'en')
    
    Returns:
    - Created ticket with unique ticket ID
    """
    try:
        ticket = await ticket_service.create_ticket(
            db=db,
            user_id=request.user_id,
            question=request.question,
            category=request.category,
            language=request.language or 'en'
        )
        
        logger.info(f"Ticket created: {ticket.ticket_id}")
        
        return ticket
        
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {str(e)}"
        )


@router.get("/{ticket_id}", response_model=TicketResponse, status_code=status.HTTP_200_OK)
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get ticket by ID
    
    - **ticket_id**: Unique ticket identifier
    
    Returns:
    - Ticket details including status and answer (if resolved)
    """
    try:
        ticket = await ticket_service.get_ticket(db, ticket_id)
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} not found"
            )
        
        return ticket
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{ticket_id}", response_model=TicketResponse, status_code=status.HTTP_200_OK)
async def update_ticket(
    ticket_id: str,
    request: TicketUpdateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update ticket (admin only)
    
    - **ticket_id**: Unique ticket identifier
    - **answer**: Admin's answer/response
    - **status**: Ticket status (open, in_progress, resolved, closed)
    - **priority**: Priority level (low, medium, high, critical)
    - **admin_id**: Admin user ID
    
    Returns:
    - Updated ticket
    
    Note: When status is set to 'resolved', the ticket is automatically
    added to the learning system if auto_learning is enabled.
    """
    try:
        ticket = await ticket_service.update_ticket(
            db=db,
            ticket_id=ticket_id,
            answer=request.answer,
            status=request.status,
            priority=request.priority,
            admin_id=request.admin_id
        )
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} not found"
            )
        
        logger.info(f"Ticket updated: {ticket_id}")
        
        return ticket
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/user/{user_id}", response_model=List[TicketResponse], status_code=status.HTTP_200_OK)
async def get_user_tickets(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all tickets for a specific user
    
    - **user_id**: User identifier
    - **limit**: Maximum number of tickets to return (1-100, default: 10)
    
    Returns:
    - List of user's tickets, ordered by creation date (newest first)
    """
    try:
        tickets = await ticket_service.get_user_tickets(
            db=db,
            user_id=user_id,
            limit=limit
        )
        
        return tickets
        
    except Exception as e:
        logger.error(f"Error getting user tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("", response_model=List[TicketResponse], status_code=status.HTTP_200_OK)
async def get_open_tickets(
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get open tickets with optional filters (admin only)
    
    - **category**: Filter by category
    - **priority**: Filter by priority level
    - **limit**: Maximum number of tickets (1-100, default: 50)
    
    Returns:
    - List of open tickets matching filters
    """
    try:
        tickets = await ticket_service.get_open_tickets(
            db=db,
            category=category,
            priority=priority,
            limit=limit
        )
        
        return tickets
        
    except Exception as e:
        logger.error(f"Error getting open tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats/overview", status_code=status.HTTP_200_OK)
async def get_ticket_stats(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get ticket statistics (admin only)
    
    Returns:
    - Total tickets count
    - Breakdown by status
    - Average resolution time
    - Category distribution
    """
    try:
        stats = await ticket_service.get_ticket_stats(db)
        return stats
        
    except Exception as e:
        logger.error(f"Error getting ticket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
