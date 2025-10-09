"""
Google Drive Upload Routes
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import httpx
import mimetypes

router = APIRouter(prefix="/api", tags=["Google Drive"])

@router.post("/upload-to-drive")
async def upload_to_drive(
    file: UploadFile = File(...),
    accessToken: str = Form(...),
    folderId: str = Form(...)
):
    """
    Upload file to Google Drive
    
    Args:
        file: PDF file to upload
        accessToken: Google Drive access token
        folderId: Target folder ID in Google Drive
    
    Returns:
        Success status and file details
    """
    try:
        print(f"📤 Uploading to Drive folder: {folderId}")
        print(f"📄 Filename: {file.filename}")
        print(f"🔑 Token: {accessToken[:20]}...")
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        print(f"📊 File size: {file_size / 1024:.2f} KB")
        
        # Validate token format
        if not accessToken.startswith('ya29'):
            raise HTTPException(400, "Invalid Google access token format")
        
        # Step 1: Create metadata
        metadata = {
                "name": file.filename,
                "parents": ["root"] if not folderId or folderId == "root" else [folderId],
                "mimeType": "application/pdf"
            }
        
        # Step 2: Upload using multipart upload
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Prepare multipart form data
            files = {
                'data': ('metadata', 
                        str(metadata).replace("'", '"'),  # Convert dict to JSON string
                        'application/json; charset=UTF-8'),
                'file': (file.filename, file_content, 'application/pdf')
            }
            
            # Upload to Drive
            response = await client.post(
                'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
                headers={
                    'Authorization': f'Bearer {accessToken}'
                },
                files=files
            )
            
            if response.status_code not in [200, 201]:
                error_detail = response.text
                print(f"❌ Upload failed: {error_detail}")
                raise HTTPException(response.status_code, f"Drive upload failed: {error_detail}")
            
            result = response.json()
            file_id = result.get('id')
            
            print(f"✅ File uploaded successfully: {file_id}")
            
            # Generate web view link
            web_view_link = f"https://drive.google.com/file/d/{file_id}/view"
            
            return JSONResponse({
                "success": True,
                "fileId": file_id,
                "fileName": file.filename,
                "webViewLink": web_view_link,
                "message": "File uploaded to Google Drive successfully"
            })
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Upload failed: {str(e)}")