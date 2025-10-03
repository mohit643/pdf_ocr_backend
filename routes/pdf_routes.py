"""
PDF Routes - Complete Implementation with Google Drive Integration
"""
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
import uuid
import os
import json

from database import get_db
from google_drive import upload_to_drive
from models import User
from schemas import DownloadRequest, PDFListResponse
from auth import get_current_user
from config import settings
from utils.pdf_processor import (
    extract_text_blocks, render_page_as_image, 
    save_thumbnail, apply_text_edits, apply_signatures
)
import crud
import fitz

router = APIRouter(prefix="/api", tags=["PDF"])

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and process PDF - Auto-upload to centralized Drive"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    
    try:
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stored_filename = f"{timestamp}_{session_id[:8]}_{file.filename}"
        file_path = settings.UPLOAD_DIR / stored_filename
        
        print(f"📤 Upload by {current_user.email} - Session: {session_id}")
        
        # Save file locally
        file_data = await file.read()
        file_size = len(file_data)
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Get PDF metadata
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        doc.close()
        
        # Save to database
        pdf_record = crud.create_pdf(
            db=db,
            user_id=current_user.id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size=file_size,
            total_pages=total_pages,
            session_id=session_id
        )
        
        # ========== UPLOAD TO CENTRALIZED DRIVE ==========
        drive_file_id = None
        drive_link = None
        
        try:
            print(f"☁️ Uploading to Drive for: {current_user.email}")
            
            drive_result = upload_to_drive(
                file_path=str(file_path),
                user_email=current_user.email,
                filename=stored_filename
            )
            
            if drive_result:
                drive_file_id = drive_result['file_id']
                drive_link = drive_result.get('web_view_link')
                print(f"✅ Drive upload success: {drive_file_id}")
            else:
                print("⚠️ Drive upload returned None")
                
        except Exception as e:
            print(f"⚠️ Drive upload failed (continuing): {e}")
        
        # Process all pages
        all_pages = []
        for page_num in range(total_pages):
            page_img = render_page_as_image(str(file_path), page_num, 2.0)
            text_blocks = extract_text_blocks(str(file_path), page_num)
            
            thumb_filename = f"{session_id}_page_{page_num}.png"
            thumb_path = settings.THUMBNAIL_DIR / thumb_filename
            save_thumbnail(str(file_path), page_num, str(thumb_path))
            
            thumb_img = render_page_as_image(str(file_path), page_num, 0.3)
            
            crud.create_pdf_page(
                db=db,
                pdf_id=pdf_record.id,
                page_number=page_num,
                width=page_img['width'],
                height=page_img['height'],
                thumbnail_path=str(thumb_path),
                text_blocks=text_blocks
            )
            
            all_pages.append({
                'page_num': page_num,
                'image': page_img['image'],
                'thumbnail': thumb_img['image'],
                'width': page_img['width'],
                'height': page_img['height'],
                'text_blocks': text_blocks
            })
        
        # Log activity
        crud.log_activity(
            db=db,
            action="upload",
            details={
                "filename": file.filename,
                "size": file_size,
                "pages": total_pages,
                "drive_file_id": drive_file_id,
                "drive_link": drive_link
            },
            pdf_id=pdf_record.id,
            user_id=current_user.id
        )
        
        print(f"✅ Upload complete - {total_pages} pages")
        
        return JSONResponse({
            'success': True,
            'session_id': session_id,
            'pdf_id': pdf_record.id,
            'filename': file.filename,
            'total_pages': total_pages,
            'drive_uploaded': drive_file_id is not None,
            'drive_link': drive_link,
            'pages': all_pages
        })
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.post("/download")
async def download_pdf(
    request: DownloadRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download edited PDF and upload to Drive"""
    if len(request.edits) == 0 and len(request.signatures) == 0:
        raise HTTPException(400, "No changes to save")
    
    pdf_record = crud.get_pdf_by_session(db, request.session_id)
    if not pdf_record:
        raise HTTPException(404, "PDF not found")
    
    if pdf_record.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    
    try:
        original_path = pdf_record.file_path
        
        if not Path(original_path).exists():
            raise HTTPException(404, "Original PDF file not found")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"edited_{timestamp}_{pdf_record.original_filename}"
        output_path = settings.OUTPUT_DIR / output_filename
        
        temp_filename = f"temp_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
        temp_path = settings.OUTPUT_DIR / temp_filename
        
        current_input = original_path
        
        # Apply text edits
        if len(request.edits) > 0:
            success = apply_text_edits(current_input, request.edits, str(temp_path))
            if not success:
                raise HTTPException(500, "Failed to apply text edits")
            current_input = str(temp_path)
        
        # Apply signatures
        if len(request.signatures) > 0:
            if current_input == original_path:
                import shutil
                shutil.copy(original_path, temp_path)
                current_input = str(temp_path)
            
            success = apply_signatures(current_input, request.signatures, str(output_path))
            if not success:
                if Path(temp_path).exists():
                    os.remove(temp_path)
                raise HTTPException(500, "Failed to apply signatures")
        else:
            import shutil
            shutil.move(temp_path, output_path)
        
        # Cleanup temp file
        if Path(temp_path).exists() and Path(temp_path) != Path(output_path):
            try:
                os.remove(temp_path)
            except:
                pass
        
        output_size = os.path.getsize(output_path)
        
        # Save version to database
        edits_data = [edit.dict() for edit in request.edits]
        sigs_data = [sig.dict() for sig in request.signatures]
        
        version = crud.create_pdf_version(
            db=db,
            original_pdf_id=pdf_record.id,
            stored_filename=output_filename,
            file_path=str(output_path),
            file_size=output_size,
            edits_data=edits_data + sigs_data
        )
        
        # ========== UPLOAD EDITED PDF TO DRIVE ==========
        drive_file_id = None
        drive_link = None
        
        try:
            print(f"☁️ Uploading edited PDF to Drive for: {current_user.email}")
            
            drive_result = upload_to_drive(
                file_path=str(output_path),
                user_email=current_user.email,
                filename=output_filename
            )
            
            if drive_result:
                drive_file_id = drive_result['file_id']
                drive_link = drive_result.get('web_view_link')
                print(f"✅ Edited PDF uploaded: {drive_file_id}")
            
        except Exception as e:
            print(f"⚠️ Drive upload failed: {e}")
        
        return FileResponse(
            str(output_path),
            media_type='application/pdf',
            filename=output_filename,
            headers={
                "X-Version-ID": str(version.id),
                "X-Version-Number": str(version.version_number),
                "X-Drive-Link": drive_link or "not-uploaded"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        raise HTTPException(500, f"Download failed: {str(e)}")


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