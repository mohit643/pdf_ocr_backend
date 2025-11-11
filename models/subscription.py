"""
Subscription models for managing user subscriptions and plans
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    
    # Primary Key - Changed from UUID to String for SQLite compatibility
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Plan Details
    name = Column(String(50), unique=True, nullable=False)  # free, pro
    display_name = Column(String(100), nullable=False)
    description = Column(String(500))
    
    # Pricing
    price = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    billing_period = Column(String(20), default="monthly")  # monthly, yearly
    
    # Features
    pdf_limit = Column(Integer, default=3)  # -1 for unlimited
    features = Column(String(1000))  # JSON string of features
    
    # Stripe
    stripe_price_id = Column(String(255))
    stripe_product_id = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="plan")
    
    def __repr__(self):
        return f"<SubscriptionPlan(name={self.name}, price={self.price})>"
    
    def to_dict(self):
        """Convert SubscriptionPlan to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "price": self.price,
            "currency": self.currency,
            "billing_period": self.billing_period,
            "pdf_limit": self.pdf_limit,
            "features": self.features,
            "stripe_price_id": self.stripe_price_id,
            "stripe_product_id": self.stripe_product_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    
    # Primary Key - Changed from UUID to String for SQLite compatibility
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign Keys
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=False)
    
    # Subscription Status
    status = Column(String(20), default="active")  # active, cancelled, expired, past_due
    
    # Stripe
    stripe_subscription_id = Column(String(255), unique=True)
    stripe_customer_id = Column(String(255))
    
    # Dates
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    
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
