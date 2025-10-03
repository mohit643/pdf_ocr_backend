"""
Statistics and Search Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import json

from database import get_db
from models import User, PDF, PDFVersion
from schemas import PDFListResponse
from auth import get_current_user, get_optional_user
import crud

router = APIRouter(prefix="/api", tags=["Statistics"])

@router.get("/pdfs", response_model=PDFListResponse)
async def list_pdfs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get PDFs for current user only"""
    pdfs = crud.get_user_pdfs(db, user_id=current_user.id, skip=skip, limit=limit)
    return {"total": len(pdfs), "pdfs": pdfs}

@router.get("/search")
async def search_pdfs(
    q: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search PDFs by filename - only current user's PDFs"""
    if not q or len(q) < 2:
        raise HTTPException(400, "Search query too short")
    
    results = crud.search_user_pdfs(db, user_id=current_user.id, query=q)
    return {"query": q, "total": len(results), "results": results}

@router.get("/pdfs/{pdf_id}/versions")
async def get_pdf_versions(
    pdf_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all versions of a PDF - only if user owns it"""
    pdf = crud.get_pdf_by_id(db, pdf_id)
    if not pdf:
        raise HTTPException(404, "PDF not found")
    
    if pdf.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    
    versions = crud.get_pdf_versions(db, pdf_id)
    return {
        "pdf_id": pdf_id,
        "original_filename": pdf.original_filename,
        "total_versions": len(versions),
        "versions": versions
    }

@router.get("/pdfs/{pdf_id}/pages")
async def get_pdf_pages(
    pdf_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pages of a PDF - only if user owns it"""
    pdf = crud.get_pdf_by_id(db, pdf_id)
    if not pdf:
        raise HTTPException(404, "PDF not found")
    
    if pdf.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    
    pages = crud.get_pdf_pages(db, pdf_id)
    
    pages_data = []
    for page in pages:
        pages_data.append({
            "page_number": page.page_number,
            "width": page.width,
            "height": page.height,
            "thumbnail_path": page.thumbnail_path,
            "text_blocks": json.loads(page.text_blocks) if page.text_blocks else []
        })
    
    return {"pdf_id": pdf_id, "total_pages": len(pages_data), "pages": pages_data}

@router.get("/stats")
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get statistics - user-specific if logged in, global if not"""
    if current_user:
        # User-specific stats
        total_pdfs = db.query(func.count(PDF.id)).filter(
            PDF.is_active == True,
            PDF.user_id == current_user.id
        ).scalar()
        
        total_versions = db.query(func.count(PDFVersion.id)).join(PDF).filter(
            PDF.user_id == current_user.id
        ).scalar()
        
        total_storage = db.query(func.sum(PDF.file_size)).filter(
            PDF.is_active == True,
            PDF.user_id == current_user.id
        ).scalar() or 0
    else:
        # Global stats
        total_pdfs = db.query(func.count(PDF.id)).filter(PDF.is_active == True).scalar()
        total_versions = db.query(func.count(PDFVersion.id)).scalar()
        total_storage = db.query(func.sum(PDF.file_size)).filter(PDF.is_active == True).scalar() or 0
    
    return {
        "total_pdfs": total_pdfs,
        "total_versions": total_versions,
        "total_storage_bytes": total_storage,
        "total_storage_mb": round(total_storage / (1024 * 1024), 2)
    }

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check"""
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    return {'status': 'healthy', 'database': db_status, 'version': '4.0'}