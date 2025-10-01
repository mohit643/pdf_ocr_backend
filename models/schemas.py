"""
Pydantic Schemas - Data models
Save as: backend/models/schemas.py
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class TextEdit(BaseModel):
    """Text edit model"""
    page: int = Field(..., description="Page number")
    bbox: List[float] = Field(..., description="Bounding box")
    old_text: str = Field(..., description="Original text")
    new_text: str = Field(..., description="New text")
    fontSize: int = Field(12, description="Font size")
    color: Optional[str] = Field("#000000", description="Color")


class DownloadRequest(BaseModel):
    """Download request model"""
    session_id: str = Field(..., description="Session ID")
    edits: List[TextEdit] = Field(..., description="List of edits")


class TextBlock(BaseModel):
    """Text block model"""
    text: str
    bbox: List[float]
    font: str
    size: float
    color: int


class PageData(BaseModel):
    """Page data model"""
    page_num: int
    image: str
    thumbnail: Optional[str] = None
    width: int
    height: int
    text_blocks: List[TextBlock]


class PDFUploadResponse(BaseModel):
    """Upload response model"""
    success: bool
    session_id: str
    filename: str
    total_pages: int
    pages: List[PageData]


class PageResponse(BaseModel):
    """Single page response"""
    page_num: int
    image: str
    thumbnail: Optional[str]
    width: int
    height: int
    text_blocks: List[TextBlock]