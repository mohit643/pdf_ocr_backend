"""
Models Package
"""

# Pydantic Schemas (for API requests/responses)
from .schemas import (
    TextEdit,
    DownloadRequest,
    PDFUploadResponse,
    PageResponse
)

# ✅ NEW: SQLAlchemy Database Models
from .user import User
from .subscription import SubscriptionPlan, UserSubscription

__all__ = [
    # Pydantic Schemas
    'TextEdit',
    'DownloadRequest',
    'PDFUploadResponse',
    'PageResponse',
    # ✅ NEW: Database Models
    'User',
    'SubscriptionPlan',
    'UserSubscription'
]