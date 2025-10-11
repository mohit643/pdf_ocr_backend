from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from typing import Optional
import io
from pathlib import Path
from routes.auth_routes import router as auth_router
from routes.pdf_routes import router as pdf_router
from routes.drive import router as drive_router

# Import database - ✅ NEW
from database import init_db, close_db

# Import your routers
from routes.auth_routes import router as auth_router
from routes.pdf_routes import router as pdf_router
from routes.drive import router as drive_router
from routes.subscription_routes import router as subscription_router  # ✅ NEW
from routes.payment_routes import router as payment_router  # ✅ NEW

app = FastAPI(title="PDF Editor API", version="5.0")  # ✅ Changed version

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",  # ✅ NEW
        # "https://document-read-production.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # ✅ NEW
)

# Create directories if not exist
Path("outputs").mkdir(exist_ok=True)
Path("uploads").mkdir(exist_ok=True)
Path("thumbnails").mkdir(exist_ok=True)

# Mount static directories
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/thumbnails", StaticFiles(directory="thumbnails"), name="thumbnails")

# Include routers
app.include_router(auth_router)
app.include_router(pdf_router)
app.include_router(drive_router)
app.include_router(subscription_router)  # ✅ NEW
app.include_router(payment_router)  # ✅ NEW

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("PDF Editor API Starting with OAuth & Subscriptions...")  # ✅ Updated message
    print("=" * 60)
    
    # ✅ NEW: Initialize database
    await init_db()
    
    # ✅ NEW: Initialize subscription plans
    from database import AsyncSessionLocal
    from services.subscription_service import SubscriptionService
    from config import settings
    
    async with AsyncSessionLocal() as db:
        try:
            # Create Free Plan
            await SubscriptionService.get_or_create_plan(
                db=db,
                name="free",
                display_name="Free Plan",
                description="Perfect for trying out our PDF editor",
                price=0.0,
                pdf_limit=settings.PLAN_FREE_LIMIT
            )
            
            # Create Basic Plan
            await SubscriptionService.get_or_create_plan(
                db=db,
                name="basic",
                display_name="Basic Plan",
                description="For regular users",
                price=settings.PLAN_BASIC_PRICE,
                pdf_limit=settings.PLAN_BASIC_LIMIT,
              stripe_price_id="price_1SGZRZ3NlamZyfzGvvCrzEig"
            )
            
            # Create Pro Plan
            await SubscriptionService.get_or_create_plan(
                db=db,
                name="pro",
                display_name="Pro Plan",
                description="Unlimited PDF processing",
                price=settings.PLAN_PRO_PRICE,
                pdf_limit=settings.PLAN_PRO_LIMIT,
                 stripe_price_id="price_1SGZRy3NlamZyfzGTjyp9hj3" 
            )
            
            print("✅ Subscription plans initialized")
        except Exception as e:
            print(f"⚠️ Plan initialization warning: {e}")
    
    try:
        from config import settings
        print(f"📁 Upload folder: {settings.UPLOAD_DIR.absolute()}")
        print(f"📁 Output folder: {settings.OUTPUT_DIR.absolute()}")
        print(f"📁 Thumbnail folder: {settings.THUMBNAIL_DIR.absolute()}")
        print(f"🗄️  Database: Connected")  # ✅ NEW
    except:
        print(f"📁 Upload folder: {Path('uploads').absolute()}")
        print(f"📁 Output folder: {Path('outputs').absolute()}")
        print(f"📁 Thumbnail folder: {Path('thumbnails').absolute()}")
    
    print("=" * 60)
    print("✅ Available Endpoints:")
    print("   - GET  /                           (Root)")
    print("   - GET  /api/stats                  (Statistics)")
    print("   - POST /api/upload                 (Upload PDF)")
    print("   - POST /api/download               (Download Edited PDF)")
    print("   - POST /upload-to-drive            (Manual Drive Upload)")
    print("   - POST /list-drive-files           (List Drive Files)")
    print("   - GET  /api/subscription/plans     (Get Plans) ✅")  # ✅ NEW
    print("   - GET  /api/subscription/my-subscription (My Subscription) ✅")  # ✅ NEW
    print("   - POST /api/subscription/create-checkout (Create Checkout) ✅")  # ✅ NEW
    print("   - POST /api/payment/webhook        (Stripe Webhook) ✅")  # ✅ NEW
    print("=" * 60)

@app.on_event("shutdown")  # ✅ NEW
async def shutdown_event():
    await close_db()
    print("🔒 Application shutdown complete")

@app.get("/")
def root():
    return {
        "app": "PDF Editor API",
        "version": "5.0",  # ✅ Updated version
        "status": "running",
        "oauth": "enabled",
        "features": ["oauth", "subscriptions", "stripe"],  # ✅ NEW
        "endpoints": {
            "stats": "/api/stats",
            "upload": "/api/upload",
            "download": "/api/download",
            "drive_upload": "/upload-to-drive",
            "drive_list": "/list-drive-files",
            "subscription_plans": "/api/subscription/plans",  # ✅ NEW
            "my_subscription": "/api/subscription/my-subscription",  # ✅ NEW
            "create_checkout": "/api/subscription/create-checkout",  # ✅ NEW
            "stripe_webhook": "/api/payment/webhook"  # ✅ NEW
        }
    }

@app.post("/upload-to-drive")
async def upload_to_drive(
    file: UploadFile = File(...),
    accessToken: str = Form(...),
    folderId: Optional[str] = Form(None)
):
    """
    Upload file to Google Drive using access token
    
    Args:
        file: File to upload
        accessToken: Google OAuth access token from frontend
        folderId: Optional Google Drive folder ID (if None, uploads to root)
    """
    try:
        # Validate access token
        if not accessToken:
            raise HTTPException(status_code=400, detail="Access token not provided")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        print(f"☁️  Uploading to Google Drive: {file.filename}")
        
        # Create credentials using access token
        creds = Credentials(token=accessToken)
        service = build('drive', 'v3', credentials=creds)
        
        # Read file content
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)
        
        # Prepare file metadata
        file_metadata = {'name': file.filename}
        
        # Add folder parent if provided
        if folderId:
            file_metadata['parents'] = [folderId]
            print(f"📂 Target folder ID: {folderId}")
        
        # Create media upload
        media = MediaIoBaseUpload(
            file_stream,
            mimetype=file.content_type or 'application/octet-stream',
            resumable=True
        )
        
        # Upload file to Google Drive
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, mimeType, size'
        ).execute()
        
        print(f"✅ Successfully uploaded: {uploaded_file.get('webViewLink')}")
        
        return {
            "success": True,
            "message": "File uploaded successfully to Google Drive!",
            "fileId": uploaded_file.get('id'),
            "fileName": uploaded_file.get('name'),
            "webViewLink": uploaded_file.get('webViewLink'),
            "mimeType": uploaded_file.get('mimeType'),
            "size": uploaded_file.get('size')
        }
    
    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/list-drive-files")
async def list_drive_files(
    accessToken: str = Form(...),
    folderId: Optional[str] = Form(None),
    pageSize: int = Form(10)
):
    """
    List files from Google Drive
    
    Args:
        accessToken: Google OAuth access token
        folderId: Optional folder ID to list files from
        pageSize: Number of files to return (default: 10)
    """
    try:
        if not accessToken:
            raise HTTPException(status_code=400, detail="Access token not provided")
        
        print(f"📂 Listing Google Drive files...")
        
        creds = Credentials(token=accessToken)
        service = build('drive', 'v3', credentials=creds)
        
        # Build query
        query = ""
        if folderId:
            query = f"'{folderId}' in parents"
            print(f"📁 Folder ID: {folderId}")
        
        # List files
        results = service.files().list(
            q=query,
            pageSize=pageSize,
            fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
            orderBy="modifiedTime desc"
        ).execute()
        
        files = results.get('files', [])
        
        print(f"✅ Found {len(files)} files")
        
        return {
            "success": True,
            "message": "Files retrieved successfully",
            "count": len(files),
            "files": files
        }
    
    except Exception as e:
        print(f"❌ List files failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "5.0",  # ✅ Updated
        "service": "PDF Editor API",
        "features": ["oauth", "database", "subscriptions"]  # ✅ NEW
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)