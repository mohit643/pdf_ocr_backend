"""
CRUD Operations for PDF Database
Save as: backend/crud.py
"""

from sqlalchemy.orm import Session
from models import PDF, PDFVersion, PDFPage, PDFEdit, User, ActivityLog
from typing import List, Optional
import json
from datetime import datetime

# ============ PDF Operations ============

def create_pdf(
    db: Session,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    file_size: int,
    total_pages: int,
    session_id: str,
    user_id: Optional[int] = None
) -> PDF:
    """Create new PDF record"""
    pdf = PDF(
        user_id=user_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        total_pages=total_pages,
        session_id=session_id,
        status="ready"
    )
    db.add(pdf)
    db.commit()
    db.refresh(pdf)
    return pdf

def get_pdf_by_session(db: Session, session_id: str) -> Optional[PDF]:
    """Get PDF by session ID"""
    return db.query(PDF).filter(
        PDF.session_id == session_id,
        PDF.is_active == True
    ).first()

def get_pdf_by_id(db: Session, pdf_id: int) -> Optional[PDF]:
    """Get PDF by ID"""
    return db.query(PDF).filter(
        PDF.id == pdf_id,
        PDF.is_active == True
    ).first()

def get_all_pdfs(
    db: Session,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[PDF]:
    """Get all PDFs with pagination"""
    query = db.query(PDF).filter(PDF.is_active == True)
    if user_id:
        query = query.filter(PDF.user_id == user_id)
    return query.order_by(PDF.uploaded_at.desc()).offset(skip).limit(limit).all()

def delete_pdf(db: Session, pdf_id: int) -> bool:
    """Soft delete PDF"""
    pdf = get_pdf_by_id(db, pdf_id)
    if pdf:
        pdf.is_active = False
        db.commit()
        return True
    return False

def search_pdfs(
    db: Session,
    query: str,
    user_id: Optional[int] = None
) -> List[PDF]:
    """Search PDFs by filename"""
    search = f"%{query}%"
    db_query = db.query(PDF).filter(
        PDF.is_active == True,
        PDF.original_filename.ilike(search)
    )
    if user_id:
        db_query = db_query.filter(PDF.user_id == user_id)
    return db_query.order_by(PDF.uploaded_at.desc()).all()

# ============ PDF Version Operations ============

def create_pdf_version(
    db: Session,
    original_pdf_id: int,
    stored_filename: str,
    file_path: str,
    file_size: int,
    edits_data: List[dict]
) -> PDFVersion:
    """Create new PDF version"""
    # Get last version number
    last_version = db.query(PDFVersion).filter(
        PDFVersion.original_pdf_id == original_pdf_id
    ).order_by(PDFVersion.version_number.desc()).first()
    
    version_number = (last_version.version_number + 1) if last_version else 1
    
    version = PDFVersion(
        original_pdf_id=original_pdf_id,
        version_number=version_number,
        version_name=f"Version {version_number}",
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        total_edits=len(edits_data),
        edit_summary=json.dumps(edits_data)
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version

def get_pdf_versions(db: Session, pdf_id: int) -> List[PDFVersion]:
    """Get all versions of a PDF"""
    return db.query(PDFVersion).filter(
        PDFVersion.original_pdf_id == pdf_id
    ).order_by(PDFVersion.version_number.desc()).all()

# ============ PDF Page Operations ============

def create_pdf_page(
    db: Session,
    pdf_id: int,
    page_number: int,
    width: int,
    height: int,
    thumbnail_path: str,
    text_blocks: List[dict]
) -> PDFPage:
    """Create PDF page record"""
    page = PDFPage(
        pdf_id=pdf_id,
        page_number=page_number,
        width=width,
        height=height,
        thumbnail_path=thumbnail_path,
        text_blocks=json.dumps(text_blocks)
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page

def get_pdf_pages(db: Session, pdf_id: int) -> List[PDFPage]:
    """Get all pages of a PDF"""
    return db.query(PDFPage).filter(
        PDFPage.pdf_id == pdf_id
    ).order_by(PDFPage.page_number).all()

# ============ PDF Edit Operations ============

def create_pdf_edit(
    db: Session,
    version_id: int,
    page_number: int,
    bbox: List[float],
    old_text: str,
    new_text: str,
    font_size: int,
    color: str
) -> PDFEdit:
    """Create PDF edit record"""
    edit = PDFEdit(
        version_id=version_id,
        page_number=page_number,
        bbox=",".join(map(str, bbox)),
        old_text=old_text,
        new_text=new_text,
        font_size=font_size,
        color=color
    )
    db.add(edit)
    db.commit()
    db.refresh(edit)
    return edit

def get_version_edits(db: Session, version_id: int) -> List[PDFEdit]:
    """Get all edits of a version"""
    return db.query(PDFEdit).filter(
        PDFEdit.version_id == version_id
    ).order_by(PDFEdit.created_at).all()

# ============ Activity Log Operations ============

def log_activity(
    db: Session,
    action: str,
    details: dict,
    user_id: Optional[int] = None,
    pdf_id: Optional[int] = None,
    ip_address: Optional[str] = None
):
    """Log user activity"""
    log = ActivityLog(
        user_id=user_id,
        pdf_id=pdf_id,
        action=action,
        details=json.dumps(details),
        ip_address=ip_address
    )
    db.add(log)
    db.commit()

def get_activity_logs(
    db: Session,
    user_id: Optional[int] = None,
    pdf_id: Optional[int] = None,
    limit: int = 50
) -> List[ActivityLog]:
    """Get activity logs"""
    query = db.query(ActivityLog)
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    if pdf_id:
        query = query.filter(ActivityLog.pdf_id == pdf_id)
    return query.order_by(ActivityLog.created_at.desc()).limit(limit).all()

# ============ User Operations ============

def create_user(db: Session, email: str, name: str) -> User:
    """Create new user"""
    user = User(email=email, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()