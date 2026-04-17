"""
Moviroo AI Chatbot - Data Loader
Loads initial dataset and handles incremental learning from tickets
"""

import pandas as pd
import os
from typing import List, Dict, Any
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import KnowledgeBase, Ticket
from models.embedding import embedding_service
from models.vector_store import FAISSVectorStore
from config import settings
vector_store = FAISSVectorStore()
logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads and processes data from various sources:
    1. Initial dataset.csv (Q&A knowledge base)
    2. Resolved tickets (incremental learning)
    """
    
    def __init__(self):
        """Initialize data loader"""
        self.dataset_path = os.path.join(settings.data_dir, "dataset.csv")
    
    async def load_initial_dataset(self, db: AsyncSession) -> int:
        """
        Load initial dataset from CSV into knowledge base
        
        Args:
            db: Database session
        
        Returns:
            Number of entries loaded
        """
        try:
            if not os.path.exists(self.dataset_path):
                logger.warning(f"Dataset file not found: {self.dataset_path}")
                # Create sample dataset
                self._create_sample_dataset()
            
            # Read CSV
            df = pd.read_csv(self.dataset_path)
            logger.info(f"Loading {len(df)} entries from dataset")
            
            # Validate required columns
            required_cols = ['question', 'answer', 'category']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"Dataset must contain columns: {required_cols}")
            
            # Add language column if not present
            if 'language' not in df.columns:
                df['language'] = 'en'
            
            count = 0
            for _, row in df.iterrows():
                # Check if already exists
                result = await db.execute(
                    select(KnowledgeBase).where(
                        KnowledgeBase.question == row['question']
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    # Create new entry
                    kb_entry = KnowledgeBase(
                        question=row['question'],
                        answer=row['answer'],
                        category=row['category'],
                        language=row.get('language', 'en'),
                        is_active=True
                    )
                    db.add(kb_entry)
                    count += 1
            
            await db.commit()
            logger.info(f"Loaded {count} new entries into knowledge base")
            
            return count
            
        except Exception as e:
            logger.error(f"Error loading initial dataset: {e}")
            await db.rollback()
            raise
    
    def _create_sample_dataset(self):
        """Create a sample dataset for demonstration"""
        sample_data = [
            # Payment issues (English)
            {
                'question': 'My payment failed. What should I do?',
                'answer': 'If your payment failed, please check: 1) Your card has sufficient funds, 2) Your card details are correct, 3) Your card is not expired. If the issue persists, try a different payment method or contact your bank.',
                'category': 'payment',
                'language': 'en'
            },
            {
                'question': 'How do I get a refund for my cancelled ride?',
                'answer': 'Refunds for cancelled rides are processed automatically within 5-7 business days. The amount will be credited back to your original payment method. If you don\'t receive it within this timeframe, please contact our support team.',
                'category': 'payment',
                'language': 'en'
            },
            {
                'question': 'Can I change my payment method?',
                'answer': 'Yes! Go to Settings > Payment Methods > Add New Card. You can add multiple payment methods and set a default one. You can also remove old payment methods from the same menu.',
                'category': 'payment',
                'language': 'en'
            },
            
            # Ride delay (English)
            {
                'question': 'My driver is late. What can I do?',
                'answer': 'We apologize for the delay. You can: 1) Track your driver\'s location in real-time on the map, 2) Contact the driver directly using the in-app call button, 3) Cancel the ride without penalty if the driver is more than 10 minutes late.',
                'category': 'ride_delay',
                'language': 'en'
            },
            {
                'question': 'The estimated arrival time keeps changing. Why?',
                'answer': 'Arrival times can change due to traffic conditions, road closures, or route changes. We use real-time traffic data to give you the most accurate estimate. Your driver is making their way to you as quickly as possible.',
                'category': 'ride_delay',
                'language': 'en'
            },
            
            # Booking (English)
            {
                'question': 'How do I book a ride?',
                'answer': 'Booking a ride is easy: 1) Open the Moviroo app, 2) Enter your destination, 3) Choose your ride type (Economy, Comfort, or Premium), 4) Confirm your pickup location, 5) Tap "Request Ride". A driver will be assigned within minutes!',
                'category': 'booking',
                'language': 'en'
            },
            {
                'question': 'Can I schedule a ride in advance?',
                'answer': 'Yes! Tap "Schedule" instead of "Request Ride" and select your desired pickup time. You can schedule rides up to 30 days in advance. We\'ll send you a reminder 30 minutes before your scheduled pickup.',
                'category': 'booking',
                'language': 'en'
            },
            {
                'question': 'How do I cancel a ride?',
                'answer': 'To cancel a ride: 1) Open your active ride, 2) Tap "Cancel Ride" at the bottom, 3) Select a reason, 4) Confirm cancellation. Note: Cancellations within 2 minutes of booking are free. After that, a small cancellation fee may apply.',
                'category': 'booking',
                'language': 'en'
            },
            
            # Account (English)
            {
                'question': 'How do I create an account?',
                'answer': 'To create an account: 1) Download the Moviroo app, 2) Tap "Sign Up", 3) Enter your phone number, 4) Verify with the OTP code, 5) Complete your profile with name and email. That\'s it! You can now book rides.',
                'category': 'account',
                'language': 'en'
            },
            {
                'question': 'How do I update my profile information?',
                'answer': 'Go to Profile > Edit Profile. You can update your name, email, phone number, and profile picture. Don\'t forget to tap "Save" after making changes.',
                'category': 'account',
                'language': 'en'
            },
            
            # Password (English)
            {
                'question': 'I forgot my password. How do I reset it?',
                'answer': 'To reset your password: 1) Tap "Forgot Password" on the login screen, 2) Enter your registered email or phone number, 3) Check your email/SMS for a reset link, 4) Click the link and create a new password. Your new password must be at least 8 characters long.',
                'category': 'password',
                'language': 'en'
            },
            
            # Bugs (English)
            {
                'question': 'The app keeps crashing. What should I do?',
                'answer': 'If the app is crashing: 1) Try force-closing and reopening the app, 2) Check if you have the latest version in the App Store/Play Store, 3) Restart your phone, 4) Clear the app cache in Settings. If the issue persists, please contact support with your device model and OS version.',
                'category': 'bug',
                'language': 'en'
            },
            
            # French translations
            {
                'question': 'Mon paiement a échoué. Que dois-je faire?',
                'answer': 'Si votre paiement a échoué, veuillez vérifier: 1) Votre carte a des fonds suffisants, 2) Les détails de votre carte sont corrects, 3) Votre carte n\'est pas expirée. Si le problème persiste, essayez un autre mode de paiement ou contactez votre banque.',
                'category': 'payment',
                'language': 'fr'
            },
            {
                'question': 'Comment réserver une course?',
                'answer': 'Réserver une course est facile: 1) Ouvrez l\'application Moviroo, 2) Entrez votre destination, 3) Choisissez votre type de course, 4) Confirmez votre lieu de prise en charge, 5) Appuyez sur "Demander une course". Un chauffeur sera assigné en quelques minutes!',
                'category': 'booking',
                'language': 'fr'
            },
            {
                'question': 'J\'ai oublié mon mot de passe. Comment le réinitialiser?',
                'answer': 'Pour réinitialiser votre mot de passe: 1) Appuyez sur "Mot de passe oublié" sur l\'écran de connexion, 2) Entrez votre email ou numéro de téléphone enregistré, 3) Vérifiez votre email/SMS pour un lien de réinitialisation, 4) Cliquez sur le lien et créez un nouveau mot de passe.',
                'category': 'password',
                'language': 'fr'
            },
            
            # Arabic translations
            {
                'question': 'فشل الدفع. ماذا يجب أن أفعل؟',
                'answer': 'إذا فشل الدفع، يرجى التحقق من: 1) وجود أموال كافية في بطاقتك، 2) صحة تفاصيل البطاقة، 3) عدم انتهاء صلاحية البطاقة. إذا استمرت المشكلة، جرب طريقة دفع أخرى أو اتصل بالبنك.',
                'category': 'payment',
                'language': 'ar'
            },
            {
                'question': 'كيف أحجز رحلة؟',
                'answer': 'حجز رحلة سهل: 1) افتح تطبيق Moviroo، 2) أدخل وجهتك، 3) اختر نوع الرحلة، 4) أكد موقع الاستلام، 5) اضغط على "طلب رحلة". سيتم تعيين سائق في دقائق!',
                'category': 'booking',
                'language': 'ar'
            },
            
            # Franco-Arabic
            {
                'question': 'machkel fil payement, chneya nel3ab?',
                'answer': 'Itha fama machkel fil payement: 1) Verifie elli fama flous fil carte, 2) Les détails mta3 el carte correcte, 3) El carte mazelet valide. Ken mazal fama machkel, jrreb payment method okhra walla klem el bank mte3ek.',
                'category': 'payment',
                'language': 'franco-arabic'
            },
            {
                'question': 'kifech na3mal réservation?',
                'answer': 'El réservation sehla barcha: 1) O7el Moviroo app, 2) Oktheb el destination, 3) Ikhtar type mta3 el voyage, 4) Confirmi pickup location, 5) Doboz 3ala "Request Ride". Bech yal9aw chauffeur fi dkeyeik!',
                'category': 'booking',
                'language': 'franco-arabic'
            },
        ]
        
        df = pd.DataFrame(sample_data)
        df.to_csv(self.dataset_path, index=False)
        logger.info(f"Created sample dataset with {len(df)} entries")
    
    async def load_resolved_tickets(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Load resolved tickets for incremental learning
        
        Args:
            db: Database session
        
        Returns:
            List of ticket data dictionaries
        """
        try:
            # Get all resolved tickets with answers
            result = await db.execute(
                select(Ticket).where(
                    Ticket.status == 'resolved',
                    Ticket.answer.isnot(None)
                )
            )
            tickets = result.scalars().all()
            
            ticket_data = []
            for ticket in tickets:
                data = {
                    'source': 'ticket',
                    'id': ticket.id,
                    'ticket_id': ticket.ticket_id,
                    'question': ticket.question,
                    'answer': ticket.answer,
                    'category': ticket.category,
                    'language': ticket.language,
                }
                ticket_data.append(data)
            
            logger.info(f"Loaded {len(ticket_data)} resolved tickets")
            return ticket_data
            
        except Exception as e:
            logger.error(f"Error loading resolved tickets: {e}")
            return []
    
    async def build_vector_index(self, db: AsyncSession):
        """
        Build complete vector index from knowledge base and tickets
        
        Args:
            db: Database session
        """
        try:
            logger.info("Building vector index...")
            
            all_data = []
            
            # Load knowledge base
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.is_active == True)
            )
            kb_entries = kb_result.scalars().all()
            
            for entry in kb_entries:
                data = {
                    'source': 'knowledge_base',
                    'id': entry.id,
                    'question': entry.question,
                    'answer': entry.answer,
                    'category': entry.category,
                    'language': entry.language,
                }
                all_data.append(data)
            
            logger.info(f"Added {len(kb_entries)} knowledge base entries")
            
            # Load resolved tickets
            ticket_data = await self.load_resolved_tickets(db)
            all_data.extend(ticket_data)
            
            logger.info(f"Total data points: {len(all_data)}")
            
            # Rebuild vector store
            vector_store.rebuild_index(all_data)
            
            logger.info("Vector index built successfully")
            
        except Exception as e:
            logger.error(f"Error building vector index: {e}")
            raise


# Global data loader instance
data_loader = DataLoader()
