"""
User model for managing user accounts and subscriptions
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from database import Base


class User(Base):
    __tablename__ = "users"
    
    # Primary Key - Changed from UUID to String for SQLite compatibility
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User Info
    email = Column(String(255), unique=True, nullable=False)
    google_id = Column(String(255), unique=True, nullable=True)
    google_refresh_token = Column(String(500), nullable=True)
    google_access_token = Column(String(500), nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    name = Column(String(255))
    picture = Column(String(500))
    
    # Subscription & Limits
    current_plan = Column(String(50), default="free")  # free, pro
    pdf_count_this_month = Column(Integer, default=0)
    pdf_limit = Column(Integer, default=3)  # Monthly limit
    
    # Drive Integration
    drive_folder_id = Column(String(255))
    drive_folder_link = Column(String(500))
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(email={self.email}, plan={self.current_plan})>"
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "current_plan": self.current_plan,
            "pdf_count_this_month": self.pdf_count_this_month,
            "pdf_limit": self.pdf_limit,
            "drive_folder_id": self.drive_folder_id,
            "drive_folder_link": self.drive_folder_link,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }
    
    def can_process_pdf(self) -> bool:
        """Check if user can process more PDFs this month"""
        if self.current_plan == "pro":
            return True  # Unlimited
        return self.pdf_count_this_month < self.pdf_limit
    
    def increment_pdf_count(self):
        """Increment PDF processing count"""
        self.pdf_count_this_month += 1
    
    def reset_monthly_count(self):
        """Reset PDF count (call this monthly)"""
        self.pdf_count_this_month = 0
