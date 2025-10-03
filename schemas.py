"""
Pydantic Schemas for API Validation
Save as: backend/schemas.py
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

# ============ Authentication Models ============

class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    name: Optional[str] = Field(None, description="User's full name")

class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class SendOTP(BaseModel):
    """Send OTP request"""
    email: EmailStr = Field(..., description="Email to send OTP to")

class VerifyOTP(BaseModel):
    """Verify OTP request"""
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")

class ResetPassword(BaseModel):
    """Reset password request"""
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    new_password: str = Field(..., min_length=6, description="New password (min 6 characters)")

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    """User response model"""
    id: int
    email: str
    name: Optional[str]
    google_drive_folder_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ Request Models ============

class TextEdit(BaseModel):
    """Text edit request"""
    page: int = Field(..., ge=0, description="Page number (0-indexed)")
    bbox: List[float] = Field(..., min_length=4, max_length=4, description="Bounding box [x0, y0, x1, y1]")
    old_text: str = Field(..., description="Original text")
    new_text: str = Field(..., description="New text")
    fontSize: int = Field(..., gt=0, description="Font size")
    color: Optional[str] = Field("#000000", description="Text color in hex")

class Signature(BaseModel):
    """Signature model"""
    page: int
    x: float
    y: float
    width: float
    height: float
    image: str  # base64 encoded image data URL

class DownloadRequest(BaseModel):
    """Download edited PDF request"""
    session_id: str = Field(..., description="Session ID from upload")
    edits: List[TextEdit] = Field(default=[], description="List of text edits")
    signatures: List[Signature] = Field(default=[], description="List of signatures")

class UserCreate(BaseModel):
    """Create user request"""
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")

# ============ Response Models ============

class PDFResponse(BaseModel):
    """PDF response model"""
    id: int
    original_filename: str
    stored_filename: str
    file_size: int
    total_pages: int
    session_id: str
    status: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

class PDFVersionResponse(BaseModel):
    """PDF version response model"""
    id: int
    original_pdf_id: int
    version_number: int
    version_name: Optional[str]
    file_size: int
    total_edits: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class PDFPageResponse(BaseModel):
    """PDF page response model"""
    id: int
    pdf_id: int
    page_number: int
    width: int
    height: int
    thumbnail_path: str
    
    class Config:
        from_attributes = True

class PDFEditResponse(BaseModel):
    """PDF edit response model"""
    id: int
    version_id: int
    page_number: int
    bbox: str
    old_text: str
    new_text: str
    font_size: int
    color: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ActivityLogResponse(BaseModel):
    """Activity log response model"""
    id: int
    action: str
    details: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ List Response Models ============

class PDFListResponse(BaseModel):
    """List of PDFs response"""
    total: int
    pdfs: List[PDFResponse]

class PDFVersionListResponse(BaseModel):
    """List of PDF versions response"""
    pdf_id: int
    original_filename: str
    total_versions: int
    versions: List[PDFVersionResponse]

class ActivityLogListResponse(BaseModel):
    """List of activity logs response"""
    total: int
    logs: List[ActivityLogResponse]

# ============ Statistics Models ============

class StatsResponse(BaseModel):
    """Statistics response"""
    total_pdfs: int
    total_versions: int
    total_storage_bytes: int
    total_storage_mb: float

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    version: str

# ============ Search Models ============

class SearchResponse(BaseModel):
    """Search results response"""
    query: str
    total: int
    results: List[PDFResponse]

# ============ Upload Response ============

class UploadResponse(BaseModel):
    """Upload response"""
    success: bool
    session_id: str
    pdf_id: int
    filename: str
    total_pages: int
    pages: List[dict]  # Dynamic page data