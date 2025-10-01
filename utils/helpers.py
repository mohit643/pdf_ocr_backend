"""
Helper Utilities
Save as: backend/utils/helpers.py
"""

import uuid
import hashlib
from pathlib import Path


def generate_session_id() -> str:
    """Generate unique session ID"""
    return str(uuid.uuid4())


def validate_pdf_file(filename: str) -> bool:
    """Validate if file is PDF"""
    return filename.lower().endswith('.pdf')


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def clean_filename(filename: str) -> str:
    """Clean filename for safe storage"""
    import re
    filename = re.sub(r'[^\w\s.-]', '', filename)
    return filename.strip()


def get_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()