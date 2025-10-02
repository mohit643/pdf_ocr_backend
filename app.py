"""
Complete PDF Editor Backend with Signature Support
Save as: backend/app.py
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import fitz  # PyMuPDF
import os
import uuid
import base64
import json
from pathlib import Path
from datetime import datetime
import io
from PIL import Image

# Import local modules
from database import get_db, init_db, check_db_connection
from models import PDF, PDFVersion
import crud
from schemas import TextEdit, DownloadRequest, PDFResponse, PDFListResponse, Signature
from config import settings

app = FastAPI(title="PDF Editor API", version="3.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories AFTER creating app but BEFORE routes
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/thumbnails", StaticFiles(directory="thumbnails"), name="thumbnails")

# ============ Startup ============

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("=" * 60)
    print("🚀 PDF Editor API Starting...")
    print("=" * 60)
    
    if check_db_connection():
        print("✅ Database connected")
        init_db()
    else:
        print("❌ Database connection failed!")
    
    print(f"📁 Upload folder: {settings.UPLOAD_DIR.absolute()}")
    print(f"📁 Output folder: {settings.OUTPUT_DIR.absolute()}")
    print(f"📁 Thumbnail folder: {settings.THUMBNAIL_DIR.absolute()}")
    print("=" * 60)

# ============ Helper Functions ============

def extract_text_blocks(pdf_path: str, page_num: int) -> List[dict]:
    """Extract text blocks with positions"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        text_dict = page.get_text("dict")
        text_blocks = []
        
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_name = span.get('font', '').lower()
                        flags = span.get('flags', 0)
                        
                        text_blocks.append({
                            'text': span['text'],
                            'bbox': span['bbox'],
                            'font': span['font'],
                            'size': span['size'],
                            'color': span.get('color', 0),
                            'bold': 'bold' in font_name or (flags & 16),
                            'italic': 'italic' in font_name or (flags & 2),
                            'flags': flags
                        })
        
        doc.close()
        return text_blocks
    except Exception as e:
        print(f"Error extracting text: {e}")
        return []

def render_page_as_image(pdf_path: str, page_num: int, zoom: float = 2.0) -> dict:
    """Render PDF page as base64 image"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        result = {
            'image': f'data:image/png;base64,{img_base64}',
            'width': pix.width,
            'height': pix.height
        }
        
        doc.close()
        return result
    except Exception as e:
        print(f"Error rendering page: {e}")
        return None

def save_thumbnail(pdf_path: str, page_num: int, output_path: str) -> bool:
    """Save thumbnail to file"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        mat = fitz.Matrix(0.3, 0.3)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(output_path)
        doc.close()
        return True
    except:
        return False

def apply_text_edits(pdf_path: str, edits: List[TextEdit], output_path: str) -> bool:
    """Apply text edits to PDF"""
    try:
        doc = fitz.open(pdf_path)
        
        for edit in edits:
            page = doc[edit.page]
            rect = fitz.Rect(edit.bbox)
            
            # Remove old text
            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()
            
            # Parse color
            color = (0, 0, 0)
            if edit.color:
                hex_color = edit.color.lstrip('#')
                color = tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
            
            # Insert new text
            point = fitz.Point(rect.x0, rect.y0 + edit.fontSize)
            page.insert_text(point, edit.new_text, fontsize=edit.fontSize, color=color)
        
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        return True
    except Exception as e:
        print(f"Error applying edits: {e}")
        return False
    
def apply_signatures(pdf_path: str, signatures: List, output_path: str) -> bool:
    """Apply signatures to PDF"""
    print(f"\n{'='*60}")
    print(f"APPLYING {len(signatures)} SIGNATURES")
    print(f"{'='*60}")
    
    if len(signatures) == 0:
        print("No signatures to apply")
        return True
    
    try:
        doc = fitz.open(pdf_path)
        
        for idx, sig in enumerate(signatures):
            print(f"\nSignature {idx + 1}:")
            print(f"  Page: {sig.page}, Position: ({sig.x:.1f}, {sig.y:.1f})")
            print(f"  Size: {sig.width}x{sig.height}")
            
            try:
                page = doc[sig.page]
                
                # Get base64 data
                img_data = sig.image
                if 'base64,' in img_data:
                    img_data = img_data.split('base64,')[1]
                
                # Decode
                img_bytes = base64.b64decode(img_data)
                
                # Open with PIL and convert to PNG
                img = Image.open(io.BytesIO(img_bytes))
                
                # Convert to RGB (not RGBA) for better compatibility
                if img.mode == 'RGBA':
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_bytes_final = img_byte_arr.getvalue()
                
                # Insert
                rect = fitz.Rect(sig.x, sig.y, sig.x + sig.width, sig.y + sig.height)
                page.insert_image(rect, stream=img_bytes_final)
                
                print(f"  SUCCESS!")
                
            except Exception as e:
                print(f"  FAILED: {e}")
                import traceback
                traceback.print_exc()
                # Don't return False, continue with other signatures
        
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        print(f"\nDocument saved: {output_path}")
        return True
        
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============ Routes ============

@app.get("/")
def root():
    return {
        "app": "PDF Editor API",
        "version": "3.0",
        "status": "running",
        "database": "connected" if check_db_connection() else "disconnected"
    }

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload and process PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    
    try:
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stored_filename = f"{timestamp}_{session_id[:8]}_{file.filename}"
        file_path = settings.UPLOAD_DIR / stored_filename
        
        print(f"📤 Upload started - Session: {session_id}")
        
        file_data = await file.read()
        file_size = len(file_data)
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        print(f"📁 File saved: {file_path}")
        
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        doc.close()
        
        pdf_record = crud.create_pdf(
            db=db,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size=file_size,
            total_pages=total_pages,
            session_id=session_id
        )
        
        print(f"💾 PDF saved to database - ID: {pdf_record.id}")
        
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
        
        crud.log_activity(
            db=db,
            action="upload",
            details={"filename": file.filename, "size": file_size, "pages": total_pages},
            pdf_id=pdf_record.id
        )
        
        print(f"✅ Upload complete - {total_pages} pages processed")
        
        return JSONResponse({
            'success': True,
            'session_id': session_id,
            'pdf_id': pdf_record.id,
            'filename': file.filename,
            'total_pages': total_pages,
            'pages': all_pages
        })
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@app.post("/api/download")
async def download_pdf(request: DownloadRequest, db: Session = Depends(get_db)):
    """Download edited PDF with text edits and signatures"""
    print(f"📥 Download request - Session: {request.session_id}")
    print(f"✏️ Edits: {len(request.edits)}, Signatures: {len(request.signatures)}")
    
    if len(request.edits) == 0 and len(request.signatures) == 0:
        raise HTTPException(400, "No changes to save")
    
    pdf_record = crud.get_pdf_by_session(db, request.session_id)
    
    if not pdf_record:
        raise HTTPException(404, "PDF not found or expired")
    
    try:
        original_path = pdf_record.file_path
        
        if not Path(original_path).exists():
            raise HTTPException(404, "Original PDF file not found")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"edited_{timestamp}_{pdf_record.original_filename}"
        output_path = settings.OUTPUT_DIR / output_filename
        
        # Create temp file for intermediate steps
        temp_filename = f"temp_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
        temp_path = settings.OUTPUT_DIR / temp_filename
        
        current_input = original_path
        
        # Apply text edits first
        if len(request.edits) > 0:
            print(f"✏️ Applying {len(request.edits)} text edits...")
            success = apply_text_edits(current_input, request.edits, str(temp_path))
            if not success:
                raise HTTPException(500, "Failed to apply text edits")
            current_input = str(temp_path)
        
        # Apply signatures
        if len(request.signatures) > 0:
            print(f"✍️ Applying {len(request.signatures)} signatures...")
            # If we have temp file, use it; otherwise copy original
            if current_input == original_path:
                import shutil
                shutil.copy(original_path, temp_path)
                current_input = str(temp_path)
            
            success = apply_signatures(current_input, request.signatures, str(output_path))
            if not success:
                # Cleanup temp file
                if Path(temp_path).exists():
                    os.remove(temp_path)
                raise HTTPException(500, "Failed to apply signatures")
        else:
            # No signatures, just rename temp to output
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
        
        for edit in request.edits:
            crud.create_pdf_edit(
                db=db,
                version_id=version.id,
                page_number=edit.page,
                bbox=edit.bbox,
                old_text=edit.old_text,
                new_text=edit.new_text,
                font_size=edit.fontSize,
                color=edit.color
            )
        
        crud.log_activity(
            db=db,
            action="download",
            details={
                "version_id": version.id,
                "total_edits": len(request.edits),
                "total_signatures": len(request.signatures),
                "output_size": output_size
            },
            pdf_id=pdf_record.id
        )
        
        print(f"✅ Version {version.version_number} created - ID: {version.id}")
        
        return FileResponse(
            str(output_path),
            media_type='application/pdf',
            filename=output_filename,
            headers={
                "X-Version-ID": str(version.id),
                "X-Version-Number": str(version.version_number)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Download failed: {str(e)}")

@app.get("/api/pdfs", response_model=PDFListResponse)
async def list_pdfs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all PDFs"""
    pdfs = crud.get_all_pdfs(db, skip=skip, limit=limit)
    return {"total": len(pdfs), "pdfs": pdfs}

@app.get("/api/pdfs/{pdf_id}", response_model=PDFResponse)
async def get_pdf_details(pdf_id: int, db: Session = Depends(get_db)):
    """Get PDF details"""
    pdf = crud.get_pdf_by_id(db, pdf_id)
    if not pdf:
        raise HTTPException(404, "PDF not found")
    return pdf

@app.get("/api/pdfs/{pdf_id}/versions")
async def get_pdf_versions(pdf_id: int, db: Session = Depends(get_db)):
    """Get all versions of a PDF"""
    pdf = crud.get_pdf_by_id(db, pdf_id)
    if not pdf:
        raise HTTPException(404, "PDF not found")
    
    versions = crud.get_pdf_versions(db, pdf_id)
    return {
        "pdf_id": pdf_id,
        "original_filename": pdf.original_filename,
        "total_versions": len(versions),
        "versions": versions
    }

@app.get("/api/pdfs/{pdf_id}/pages")
async def get_pdf_pages(pdf_id: int, db: Session = Depends(get_db)):
    """Get all pages of a PDF"""
    pdf = crud.get_pdf_by_id(db, pdf_id)
    if not pdf:
        raise HTTPException(404, "PDF not found")
    
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

@app.delete("/api/pdfs/{pdf_id}")
async def delete_pdf(pdf_id: int, db: Session = Depends(get_db)):
    """Delete PDF (soft delete)"""
    success = crud.delete_pdf(db, pdf_id)
    if not success:
        raise HTTPException(404, "PDF not found")
    
    crud.log_activity(db=db, action="delete", details={"pdf_id": pdf_id}, pdf_id=pdf_id)
    return {"message": "PDF deleted successfully"}

@app.get("/api/search")
async def search_pdfs(q: str, db: Session = Depends(get_db)):
    """Search PDFs by filename"""
    if not q or len(q) < 2:
        raise HTTPException(400, "Search query too short")
    
    results = crud.search_pdfs(db, q)
    return {"query": q, "total": len(results), "results": results}

@app.get("/api/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """Get database statistics"""
    from sqlalchemy import func
    
    total_pdfs = db.query(func.count(PDF.id)).filter(PDF.is_active == True).scalar()
    total_versions = db.query(func.count(PDFVersion.id)).scalar()
    total_storage = db.query(func.sum(PDF.file_size)).filter(PDF.is_active == True).scalar() or 0
    
    return {
        "total_pdfs": total_pdfs,
        "total_versions": total_versions,
        "total_storage_bytes": total_storage,
        "total_storage_mb": round(total_storage / (1024 * 1024), 2)
    }

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check with database status"""
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    return {'status': 'healthy', 'database': db_status, 'version': '3.0'}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting PDF Editor API...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)