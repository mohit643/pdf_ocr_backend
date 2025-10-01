"""
Storage Service - File operations
Save as: backend/services/storage_service.py
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta


class StorageService:
    """Service for file storage operations"""
    
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def save_file(self, file_data: bytes, filename: str) -> str:
        """Save file to storage"""
        try:
            file_path = self.base_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            return str(file_path)
            
        except Exception as e:
            raise Exception(f"Failed to save file: {str(e)}")
    
    def get_file(self, filename: str) -> Optional[bytes]:
        """Read file from storage"""
        try:
            file_path = self.base_dir / filename
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                return f.read()
                
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    
    def delete_file(self, filename: str) -> bool:
        """Delete file from storage"""
        try:
            file_path = self.base_dir / filename
            
            if file_path.exists():
                file_path.unlink()
                return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def file_exists(self, filename: str) -> bool:
        """Check if file exists"""
        file_path = self.base_dir / filename
        return file_path.exists()
    
    def list_files(self, extension: Optional[str] = None) -> List[str]:
        """List all files in storage"""
        try:
            if extension:
                return [f.name for f in self.base_dir.glob(f"*{extension}")]
            else:
                return [f.name for f in self.base_dir.iterdir() if f.is_file()]
                
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def cleanup_old_files(self, hours: int = 24) -> int:
        """Delete files older than specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            deleted_count = 0
            
            for file_path in self.base_dir.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_time < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        print(f"Deleted old file: {file_path.name}")
            
            return deleted_count
            
        except Exception as e:
            print(f"Error cleaning up files: {e}")
            return 0
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics"""
        try:
            total_size = 0
            file_count = 0
            
            for file_path in self.base_dir.iterdir():
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            return {
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'directory': str(self.base_dir.absolute())
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}   