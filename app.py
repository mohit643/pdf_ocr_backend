"""
PDF Editor Backend - FastAPI + PyMuPDF + Redis
Save this as: backend/app.py
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import fitz  # PyMuPDF
import os
import uuid
import base64
import redis
import json
from pathlib import Path

app = FastAPI(title="PDF Editor API", version="2.0")

# CORS - Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=0,
        decode_responses=False
    )
    redis_client.ping()
    print("✅ Redis connected")
except:
    print("⚠️ Redis not connected - using in-memory storage")
    redis_client = None

# In-memory fallback
sessions = {}

# Folders
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")

for folder in [UPLOAD_DIR, OUTPUT_DIR]:
    folder.mkdir(exist_ok=True)

# ============ Models ============

class TextEdit(BaseModel):
    page: int
    bbox: List[float]
    old_text: str
    new_text: str
    fontSize: int
    color: Optional[str] = "#000000"

class DownloadRequest(BaseModel):
    session_id: str
    edits: List[TextEdit]

# ============ Services ============

def save_session(session_id: str, data: dict, expiry: int = 21600):
    """Save session with 6 hour expiry"""
    try:
        if redis_client:
            redis_client.setex(
                f"session:{session_id}",
                expiry,
                json.dumps(data)
            )
            print(f"✅ Session saved to Redis: {session_id}")
        else:
            sessions[session_id] = data
            print(f"✅ Session saved to memory: {session_id}")
        return True
    except Exception as e:
        print(f"❌ Error saving session: {e}")
        return False

def get_session(session_id: str):
    """Get session"""
    try:
        if redis_client:
            data = redis_client.get(f"session:{session_id}")
            if data:
                print(f"✅ Session found in Redis: {session_id}")
                return json.loads(data)
            else:
                print(f"❌ Session not found in Redis: {session_id}")
                return None
        else:
            result = sessions.get(session_id)
            if result:
                print(f"✅ Session found in memory: {session_id}")
            else:
                print(f"❌ Session not found in memory: {session_id}")
            return result
    except Exception as e:
        print(f"❌ Error getting session: {e}")
        return None

def extract_text_blocks(pdf_path: str, page_num: int) -> List[dict]:
    """Extract text blocks with positions and styling"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        text_dict = page.get_text("dict")
        text_blocks = []
        
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        # Get font info
                        font_name = span.get('font', '').lower()
                        flags = span.get('flags', 0)
                        
                        # Detect bold and italic
                        is_bold = 'bold' in font_name or (flags & 16)
                        is_italic = 'italic' in font_name or (flags & 2)
                        
                        text_blocks.append({
                            'text': span['text'],
                            'bbox': span['bbox'],
                            'font': span['font'],
                            'size': span['size'],
                            'color': span.get('color', 0),
                            'bold': is_bold,
                            'italic': is_italic,
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

# ============ Routes ============

@app.get("/")
def root():
    return {
        "app": "PDF Editor API",
        "version": "2.0",
        "status": "running",
        "redis": "connected" if redis_client else "disabled"
    }

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    
    try:
        # Generate session
        session_id = str(uuid.uuid4())
        print(f"📤 New upload - Session ID: {session_id}")
        
        # Read and save file
        file_data = await file.read()
        filename = f"{session_id}_{file.filename}"
        file_path = UPLOAD_DIR / filename
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        print(f"📁 File saved: {file_path}")
        
        # Get total pages
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        doc.close()
        
        # Save session
        session_data = {
            'filename': file.filename,
            'file_path': str(file_path),
            'total_pages': total_pages
        }
        save_session(session_id, session_data)
        
        # Verify session was saved
        verify = get_session(session_id)
        if not verify:
            print(f"❌ Session verification failed for {session_id}")
            raise HTTPException(500, "Failed to save session")
        
        # Process all pages
        all_pages = []
        for page_num in range(total_pages):
            p_info = render_page_as_image(str(file_path), page_num, 2.0)
            t_blocks = extract_text_blocks(str(file_path), page_num)
            t_info = render_page_as_image(str(file_path), page_num, 0.3)
            all_pages.append({
                'page_num': page_num,
                'image': p_info['image'],
                'thumbnail': t_info['image'],
                'width': p_info['width'],
                'height': p_info['height'],
                'text_blocks': t_blocks
            })
        
        print(f"✅ Upload complete - {total_pages} pages processed")
        
        return JSONResponse({
            'success': True,
            'session_id': session_id,
            'filename': file.filename,
            'total_pages': total_pages,
            'pages': all_pages
        })
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@app.post("/api/download")
async def download_pdf(request: DownloadRequest):
    """Download edited PDF"""
    print(f"📥 Download request - Session: {request.session_id}, Edits: {len(request.edits)}")
    
    session_data = get_session(request.session_id)
    
    if not session_data:
        print(f"❌ Session not found: {request.session_id}")
        raise HTTPException(404, detail=f"Session {request.session_id} not found or expired")
    
    try:
        original_path = session_data['file_path']
        print(f"📄 Original file: {original_path}")
        
        if not Path(original_path).exists():
            print(f"❌ File not found: {original_path}")
            raise HTTPException(404, detail="Original PDF file not found")
        
        output_filename = f"edited_{session_data['filename']}"
        output_path = OUTPUT_DIR / output_filename
        
        print(f"✏️ Applying {len(request.edits)} edits...")
        
        # Apply edits
        success = apply_text_edits(original_path, request.edits, str(output_path))
        
        if not success:
            raise HTTPException(500, "Failed to apply edits")
        
        print(f"✅ Download ready: {output_path}")
        
        return FileResponse(
            str(output_path),
            media_type='application/pdf',
            filename=output_filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        raise HTTPException(500, f"Download failed: {str(e)}")

@app.get("/api/health")
def health_check():
    """Health check"""
    return {
        'status': 'healthy',
        'redis': redis_client.ping() if redis_client else False,
        'sessions_count': len(sessions) if not redis_client else 'N/A'
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 PDF Editor API Starting...")
    print("=" * 60)
    print(f"📁 Upload folder: {UPLOAD_DIR.absolute()}")
    print(f"📁 Output folder: {OUTPUT_DIR.absolute()}")
    print(f"💾 Redis: {'Connected' if redis_client else 'Disabled (using memory)'}")
    print("=" * 60)
    print("📄 API Docs: http://localhost:8000/docs")
    print("🌐 Open: http://localhost:8000")
    print("=" * 60)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)