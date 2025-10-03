from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # ADD THIS
    name = Column(String(255))
    google_drive_folder_id = Column(String(255))  # ADD THIS
    is_active = Column(Boolean, default=True)  # ADD THIS
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # ADD THIS
    
    pdfs = relationship("PDF", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")


class OTP(Base):  # ADD THIS ENTIRE CLASS
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    otp = Column(String(6), nullable=False)
    purpose = Column(String(50))  # 'login', 'register', 'reset_password'
    is_verified = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PDF(Base):
    __tablename__ = "pdfs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Keep nullable=True for now
    
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False, unique=True)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger)
    
    total_pages = Column(Integer)
    session_id = Column(String(100), unique=True, index=True)
    
    status = Column(String(50), default="uploaded")
    is_active = Column(Boolean, default=True)
    
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="pdfs")
    versions = relationship("PDFVersion", back_populates="original_pdf", cascade="all, delete-orphan")
    pages = relationship("PDFPage", back_populates="pdf", cascade="all, delete-orphan")

class PDFVersion(Base):
    __tablename__ = "pdf_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    original_pdf_id = Column(Integer, ForeignKey("pdfs.id"), nullable=False)
    
    version_number = Column(Integer, default=1)
    version_name = Column(String(255))
    
    stored_filename = Column(String(500), nullable=False, unique=True)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger)
    
    total_edits = Column(Integer, default=0)
    edit_summary = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    original_pdf = relationship("PDF", back_populates="versions")
    edits = relationship("PDFEdit", back_populates="version", cascade="all, delete-orphan")

class PDFPage(Base):
    __tablename__ = "pdf_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_id = Column(Integer, ForeignKey("pdfs.id"), nullable=False)
    
    page_number = Column(Integer, nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    
    thumbnail_path = Column(String(1000))
    text_blocks = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    pdf = relationship("PDF", back_populates="pages")

class PDFEdit(Base):
    __tablename__ = "pdf_edits"
    
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("pdf_versions.id"), nullable=False)
    
    page_number = Column(Integer, nullable=False)
    bbox = Column(String(200))
    old_text = Column(Text)
    new_text = Column(Text)
    font_size = Column(Integer)
    color = Column(String(20))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    version = relationship("PDFVersion", back_populates="edits")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pdf_id = Column(Integer, ForeignKey("pdfs.id"), nullable=True)
    
    action = Column(String(100))
    details = Column(Text)
    ip_address = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    user = relationship("User", back_populates="logs")