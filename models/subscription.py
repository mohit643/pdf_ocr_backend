"""
Subscription Models - Plans and User Subscriptions
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
from database import Base

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    pdf_limit = Column(Integer, nullable=False)
    stripe_price_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_subscriptions = relationship("UserSubscription", back_populates="plan")
    
    def to_dict(self):
        """Convert SubscriptionPlan to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "price": float(self.price),
            "pdf_limit": self.pdf_limit,
            "stripe_price_id": self.stripe_price_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User Reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Plan Reference
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    
    # Subscription Status
    status = Column(String(50), default="active")  # active, cancelled, expired, past_due
    
    # Stripe Integration
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    stripe_customer_id = Column(String(255), nullable=True)
    
    # Dates
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)  # None for active subscriptions
    current_period_start = Column(DateTime, default=datetime.utcnow)
    current_period_end = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="user_subscriptions")
    
    def __repr__(self):
        return f"<UserSubscription(user_id={self.user_id}, plan={self.plan_id}, status={self.status})>"
    
    def to_dict(self):
        """Convert UserSubscription to dictionary - Async safe"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "plan_id": str(self.plan_id),
            "status": self.status,
            "stripe_subscription_id": self.stripe_subscription_id,
            "stripe_customer_id": self.stripe_customer_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        if self.status != "active":
            return False
        if self.end_date and self.end_date < datetime.utcnow():
            return False
        return True