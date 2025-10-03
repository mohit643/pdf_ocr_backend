"""
PDF Editor API - Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db, check_db_connection
from config import settings

# Import routers
from routes import auth_router, pdf_router, stats_router

app = FastAPI(title="PDF Editor API", version="4.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/thumbnails", StaticFiles(directory="thumbnails"), name="thumbnails")

# Include routers
app.include_router(auth_router)
app.include_router(pdf_router)
app.include_router(stats_router)

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

@app.get("/")
def root():
    return {
        "app": "PDF Editor API",
        "version": "4.0",
        "status": "running",
        "database": "connected" if check_db_connection() else "disconnected"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting PDF Editor API...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)