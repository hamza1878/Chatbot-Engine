"""
Moviroo AI Chatbot - Ticket Service
Handles support ticket creation, updates, and learning from resolved tickets
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, desc
from datetime import datetime, timedelta
import uuid
import logging

from database.models import Ticket, Feedback
from models.vector_store import FAISSVectorStore
from config import settings

logger = logging.getLogger(__name__)

vector_store = FAISSVectorStore()
class TicketService:
    """Service for managing support tickets"""
    
    async def create_ticket(
        self,
        db: AsyncSession,
        user_id: str,
        question: str,
        category: Optional[str] = None,
        language: str = 'en'
    ) -> Ticket:
        """
        Create a new support ticket
        
        Args:
            db: Database session
            user_id: User ID
            question: User's question/issue
            category: Optional category
            language: Detected language
        
        Returns:
            Created ticket
        """
        try:
            # Generate unique ticket ID
            ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
            
            # Create ticket
            ticket = Ticket(
                ticket_id=ticket_id,
                user_id=user_id,
                question=question,
                category=category,
                language=language,
                status='open',
                priority='medium'
            )
            
            db.add(ticket)
            await db.commit()
            await db.refresh(ticket)
            
            logger.info(f"Created ticket {ticket_id} for user {user_id}")
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await db.rollback()
            raise
    
    async def get_ticket(
        self,
        db: AsyncSession,
        ticket_id: str
    ) -> Optional[Ticket]:
        """
        Get ticket by ID
        
        Args:
            db: Database session
            ticket_id: Ticket ID
        
        Returns:
            Ticket or None
        """
        try:
            result = await db.execute(
                select(Ticket).where(Ticket.ticket_id == ticket_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting ticket: {e}")
            return None
    
    async def get_user_tickets(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 10
    ) -> List[Ticket]:
        """
        Get user's tickets
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of tickets
        
        Returns:
            List of tickets
        """
        try:
            result = await db.execute(
                select(Ticket)
                .where(Ticket.user_id == user_id)
                .order_by(desc(Ticket.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting user tickets: {e}")
            return []
    
    async def update_ticket(
        self,
        db: AsyncSession,
        ticket_id: str,
        answer: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        admin_id: Optional[str] = None
    ) -> Optional[Ticket]:
        """
        Update ticket with admin response
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            answer: Admin's answer
            status: New status
            priority: New priority
            admin_id: Admin user ID
        
        Returns:
            Updated ticket or None
        """
        try:
            # Get ticket
            ticket = await self.get_ticket(db, ticket_id)
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found")
                return None
            
            # Update fields
            if answer is not None:
                ticket.answer = answer
            
            if status is not None:
                ticket.status = status
                if status == 'resolved':
                    ticket.resolved_at = datetime.now()
                    # Calculate resolution time
                    if ticket.created_at:
                        resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 60
                        ticket.resolution_time_minutes = int(resolution_time)
            
            if priority is not None:
                ticket.priority = priority
            
            if admin_id is not None:
                ticket.admin_id = admin_id
            
            ticket.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(ticket)
            
            logger.info(f"Updated ticket {ticket_id}")
            
            # If resolved and has answer, add to vector store for learning
            if status == 'resolved' and answer and settings.auto_learning_enabled:
                await self._learn_from_ticket(ticket)
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error updating ticket: {e}")
            await db.rollback()
            return None
    
    async def _learn_from_ticket(self, ticket: Ticket):
        """
        Ajoute un ticket résolu à l'index FAISS en temps-réel
        via le pipeline d'entraînement (déduplication incluse).

        Args:
            ticket: Ticket SQLAlchemy résolu
        """
        try:
            from pipelines.training_pipeline import training_pipeline
            added = training_pipeline.add_single_ticket(ticket)
            if added:
                logger.info(
                    f"✅ Ticket {ticket.ticket_id} intégré dans l'index FAISS"
                )
            else:
                logger.debug(
                    f"Ticket {ticket.ticket_id} non ajouté (doublon ou données vides)"
                )
        except Exception as e:
            logger.error(f"Erreur apprentissage ticket {ticket.ticket_id}: {e}")
    
    async def get_open_tickets(
        self,
        db: AsyncSession,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50
    ) -> List[Ticket]:
        """
        Get open tickets with optional filters
        
        Args:
            db: Database session
            category: Optional category filter
            priority: Optional priority filter
            limit: Maximum number of tickets
        
        Returns:
            List of open tickets
        """
        try:
            query = select(Ticket).where(Ticket.status == 'open')
            
            if category:
                query = query.where(Ticket.category == category)
            
            if priority:
                query = query.where(Ticket.priority == priority)
            
            query = query.order_by(desc(Ticket.created_at)).limit(limit)
            
            result = await db.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting open tickets: {e}")
            return []
    
    async def get_ticket_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get ticket statistics
        
        Args:
            db: Database session
        
        Returns:
            Statistics dictionary
        """
        try:
            # Total tickets
            total_result = await db.execute(select(Ticket))
            total_tickets = len(list(total_result.scalars().all()))
            
            # By status
            status_counts = {}
            for status in ['open', 'in_progress', 'resolved', 'closed']:
                result = await db.execute(
                    select(Ticket).where(Ticket.status == status)
                )
                status_counts[status] = len(list(result.scalars().all()))
            
            # Average resolution time
            resolved_result = await db.execute(
                select(Ticket).where(
                    and_(
                        Ticket.status == 'resolved',
                        Ticket.resolution_time_minutes.isnot(None)
                    )
                )
            )
            resolved_tickets = list(resolved_result.scalars().all())
            
            avg_resolution_time = 0
            if resolved_tickets:
                total_time = sum(t.resolution_time_minutes for t in resolved_tickets)
                avg_resolution_time = total_time / len(resolved_tickets)
            
            # By category
            category_counts = {}
            result = await db.execute(select(Ticket))
            all_tickets = list(result.scalars().all())
            for ticket in all_tickets:
                if ticket.category:
                    category_counts[ticket.category] = category_counts.get(ticket.category, 0) + 1
            
            return {
                'total_tickets': total_tickets,
                'by_status': status_counts,
                'avg_resolution_time_minutes': round(avg_resolution_time, 2),
                'by_category': category_counts,
            }
            
        except Exception as e:
            logger.error(f"Error getting ticket stats: {e}")
            return {}


# Global ticket service instance
ticket_service = TicketService()
