"""
Pydantic Schemas for Request/Response validation
"""
from pydantic import BaseModel
from typing import List, Optional

class TextEdit(BaseModel):
    page: int
    bbox: List[float]
    old_text: str
    new_text: str
    fontSize: int
    color: str = "#000000"

class Signature(BaseModel):
    id: int
    page: int
    x: float
    y: float
    width: float
    height: float
    image: str

class DownloadRequest(BaseModel):
    session_id: str
    edits: List[TextEdit] = []
    signatures: List[Signature] = []