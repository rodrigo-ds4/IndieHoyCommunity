"""
Database Models
SQLAlchemy models for users, shows, discounts and tracking
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from datetime import datetime

# Importar SupervisionQueue para poder usarlo en la consulta
# ELIMINADO: from .database import SupervisionQueue


Base = declarative_base()


class User(Base):
    """User model - customers who request discounts"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    dni = Column(Integer, unique=True, index=True, nullable=True)  # Temporarily optional
    phone = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    
    # IndieHOY specific data
    registration_date = Column(DateTime, default=datetime.now)
    how_did_you_find_us = Column(String(100), nullable=True)  # "instagram", "referral", "google", etc.
    favorite_music_genre = Column(String(100), nullable=True)
    
    # Subscription info
    subscription_active = Column(Boolean, default=True)
    monthly_fee_current = Column(Boolean, default=True)  # Up to date with monthly fee
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    payment_history = relationship("PaymentHistory", back_populates="user")


class Show(Base):
    """Show/Event model"""
    __tablename__ = "shows"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # Internal show code
    title = Column(String(200), nullable=False)
    artist = Column(String(100), nullable=False)
    venue = Column(String(100), nullable=False)
    show_date = Column(DateTime, nullable=False)  # Show date
    
    # Discount control
    max_discounts = Column(Integer, nullable=False)  # Maximum discounts available for this show
    
    # External links and additional data
    ticketing_link = Column(String(500), nullable=True)  # Ticketing platform URL
    other_data = Column(JSON, nullable=True)  # Flexible field for additional show data
    
    # Status
    active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    supervision_items = relationship("SupervisionQueue", back_populates="show")
    
    # Method to calculate remaining discounts
    def get_remaining_discounts(self, db_session: Session):
        """
        Calcula los descuentos restantes de forma robusta.
        Un descuento se considera 'reservado' (no disponible) si está en la cola de supervisión
        con estado 'pending', 'approved', o 'sent'.
        Si un supervisor lo rechaza, el cupo se libera automáticamente.
        """
        # AÑADIDO: Importamos aquí para evitar la importación circular
        from .database import SupervisionQueue

        # Contar todas las solicitudes que 'reservan' un cupo y no están rechazadas.
        reserved_count = db_session.query(SupervisionQueue).filter(
            SupervisionQueue.show_id == self.id,
            SupervisionQueue.status.in_(['pending', 'approved', 'sent'])
        ).count()
        
        return self.max_discounts - reserved_count


class SupervisionQueue(Base):
    __tablename__ = "supervision_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, nullable=False)
    user_email = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    show_description = Column(String, nullable=False)
    
    # Decision info
    decision_type = Column(String, nullable=False)  # "approved", "rejected", "needs_clarification"
    decision_source = Column(String, nullable=False)  # "prefilter_template" or "llm_generated"
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=True)
    
    # Email content
    email_subject = Column(String, nullable=False)
    email_content = Column(Text, nullable=False)
    
    # Processing info
    confidence_score = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    processing_time = Column(Float, nullable=False)
    
    # Supervision status
    status = Column(String, default="pending")  # "pending", "approved", "rejected", "sent"
    email_delivery_status = Column(String, nullable=True)  # NULL, "sent", "delivered", "failed", "bounced", "rejected"
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)
    supervisor_notes = Column(Text, nullable=True)
    
    # Relations
    show = relationship("Show", back_populates="supervision_items")
    
    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "show_description": self.show_description,
            "decision_type": self.decision_type,
            "decision_source": self.decision_source,
            "show_id": self.show_id,
            "email_subject": self.email_subject,
            "email_content": self.email_content,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "processing_time": self.processing_time,
            "status": self.status,
            "email_delivery_status": self.email_delivery_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "supervisor_notes": self.supervisor_notes,
            "show_title": self.show.title if self.show else None,
            "show_artist": self.show.artist if self.show else None
        }


class PaymentHistory(Base):
    """Payment history for users - track subscription payments"""
    __tablename__ = "payment_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Payment details
    amount_paid = Column(Float, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    payment_method = Column(String(50), nullable=False)  # "card", "transfer", "cash", etc.
    
    # Additional payment info
    description = Column(String(200), nullable=True)  # "Monthly fee", "Registration", etc.
    receipt = Column(String(500), nullable=True)  # Path/URL of receipt
    
    # Status
    confirmed = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="payment_history")


class EmailTemplate(Base):
    """
    Stores email templates that can be managed from a database.
    This allows for easy updates to email content without code changes.
    """
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(100), unique=True, nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<EmailTemplate(name='{self.template_name}')>" 