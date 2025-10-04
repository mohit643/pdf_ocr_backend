"""
Routes Package
"""
from .auth_routes import router as auth_router
from .pdf_routes import router as pdf_router

__all__ = ["auth_router", "pdf_router"]