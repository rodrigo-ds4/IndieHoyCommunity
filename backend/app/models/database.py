"""
Database Models
SQLAlchemy models for users, shows, discounts and tracking
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

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
    discount_requests = relationship("DiscountRequest", back_populates="user")
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
    discount_requests = relationship("DiscountRequest", back_populates="show")
    
    # Method to calculate remaining discounts
    def get_remaining_discounts(self, db_session):
        """Calculate remaining discounts for this show"""
        sent_count = db_session.query(DiscountRequest).filter(
            DiscountRequest.show_id == self.id,
            DiscountRequest.human_approved == True
        ).count()
        return self.max_discounts - sent_count


class DiscountRequest(Base):
    """Simplified discount request tracking"""
    __tablename__ = "discount_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=True)  # LLM will determine this
    
    # Core decision
    approved = Column(Boolean, nullable=True)  # Agent decision
    human_approved = Column(Boolean, nullable=True)  # Human approval
    
    # Additional flexible data
    other_data = Column(JSON, nullable=True)  # All other request data (reason, email, etc.)
    
    # Timestamps
    request_date = Column(DateTime, default=datetime.now)  # When request was made
    agent_approval_date = Column(DateTime, nullable=True)  # When agent decided
    
    # Relationships
    user = relationship("User", back_populates="discount_requests")
    show = relationship("Show", back_populates="discount_requests")





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