"""
PDF Routes - File-based storage with Google Drive Integration
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Header
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from datetime import datetime
import uuid
import os
import json

from config import settings
from schemas import DownloadRequest
from utils.pdf_processor import (
    extract_text_blocks, render_page_as_image, 
    save_thumbnail, apply_text_edits, apply_signatures
)
import fitz

router = APIRouter(prefix="/api", tags=["PDF"])

# In-memory storage for session data
SESSIONS = {}

# Import USERS from auth_routes to access user data
from routes.auth_routes import USERS, SESSIONS as AUTH_SESSIONS

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    """Upload and process PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    
    # Extract user from token
    user_email = None
    if authorization:
        token = authorization.replace("Bearer ", "")
        if token in AUTH_SESSIONS:
            user_email = AUTH_SESSIONS[token].get("email")
    
    try:
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stored_filename = f"{timestamp}_{session_id[:8]}_{file.filename}"
        file_path = settings.UPLOAD_DIR / stored_filename
        
        print(f"📤 Upload - Session: {session_id}")
        if user_email:
            print(f"👤 User: {user_email}")
        
        # Save file locally
        file_data = await file.read()
        file_size = len(file_data)
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Get PDF metadata
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        doc.close()
        
        # Process all pages
        all_pages = []
        for page_num in range(total_pages):
            page_img = render_page_as_image(str(file_path), page_num, 2.0)
            text_blocks = extract_text_blocks(str(file_path), page_num)
            
            thumb_filename = f"{session_id}_page_{page_num}.png"
            thumb_path = settings.THUMBNAIL_DIR / thumb_filename
            save_thumbnail(str(file_path), page_num, str(thumb_path))
            
            thumb_img = render_page_as_image(str(file_path), page_num, 0.3)
            
            all_pages.append({
                'page_num': page_num,
                'image': page_img['image'],
                'thumbnail': thumb_img['image'],
                'width': page_img['width'],
                'height': page_img['height'],
                'text_blocks': text_blocks
            })
        
        # Store session data in memory with user link
        SESSIONS[session_id] = {
            'original_filename': file.filename,
            'stored_filename': stored_filename,
            'file_path': str(file_path),
            'file_size': file_size,
            'total_pages': total_pages,
            'uploaded_at': datetime.now().isoformat(),
            'pages': all_pages,
            'user_email': user_email  # Link session to user
        }
        
        print(f"✅ Upload complete - {total_pages} pages")
        
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


@router.post("/download")
async def download_pdf(request: DownloadRequest):
    """Download edited PDF and upload to Google Drive"""
    if len(request.edits) == 0 and len(request.signatures) == 0:
        raise HTTPException(400, "No changes to save")
    
    # Get session data from memory
    session_data = SESSIONS.get(request.session_id)
    if not session_data:
        raise HTTPException(404, "Session not found")
    
    try:
        original_path = session_data['file_path']
        
        if not Path(original_path).exists():
            raise HTTPException(404, "Original PDF file not found")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"edited_{timestamp}_{session_data['original_filename']}"
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
        
        # Upload to Google Drive
        drive_link = None
        drive_file_id = None
        
        try:
            # Get user from session
            user_email = session_data.get('user_email')
            
            if user_email and user_email in USERS:
                user_data = USERS[user_email]
                
                if user_data.get("drive_access_token"):
                    from services.drive_service import DriveService
                    
                    print(f"☁️ Uploading to Drive for: {user_email}")
                    
                    drive = DriveService(
                        user_data["drive_access_token"],
                        user_data.get("drive_refresh_token")
                    )
                    
                    drive_result = drive.upload_file(
                        str(output_path),
                        folder_id=user_data.get("drive_folder_id"),
                        file_name=output_filename
                    )
                    
                    if drive_result:
                        drive_link = drive_result['view_link']
                        drive_file_id = drive_result['id']
                        print(f"✅ Uploaded to Drive: {drive_link}")
                else:
                    print(f"⚠️ No Drive token for user: {user_email}")
            else:
                print(f"⚠️ No user linked to session")
                
        except Exception as e:
            print(f"⚠️ Drive upload failed (continuing): {e}")
            import traceback
            traceback.print_exc()
        
        return FileResponse(
            str(output_path),
            media_type='application/pdf',
            filename=output_filename,
            headers={
                "X-Drive-Link": drive_link or "not-uploaded",
                "X-Drive-File-ID": drive_file_id or ""
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        raise HTTPException(500, f"Download failed: {str(e)}")


@router.get("/stats")
async def get_stats():
    """Get basic statistics"""
    total_sessions = len(SESSIONS)
    total_files = sum(1 for _ in settings.UPLOAD_DIR.glob("*.pdf"))
    
    return {
        "active_sessions": total_sessions,
        "total_files": total_files
    }