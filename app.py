"""
PDF Editor API - Main Application with OAuth
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from routes import auth_router, pdf_router

import os


app = FastAPI(title="PDF Editor API", version="4.0")

# CORS
app.add_middleware(
    CORSMiddleware,
   allow_origins=[
        "http://localhost:3000",
        "https://document-read-production.up.railway.app",  # Add this
    ],
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

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("PDF Editor API Starting with OAuth...")
    print("=" * 60)
    print(f"Upload folder: {settings.UPLOAD_DIR.absolute()}")
    print(f"Output folder: {settings.OUTPUT_DIR.absolute()}")
    print(f"Thumbnail folder: {settings.THUMBNAIL_DIR.absolute()}")
    print("=" * 60)

@app.get("/")
def root():
    return {
        "app": "PDF Editor API",
        "version": "4.0",
        "status": "running",
        "oauth": "enabled"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)