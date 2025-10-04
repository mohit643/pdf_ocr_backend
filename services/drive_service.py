"""
Google Drive Service
"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from pathlib import Path
from config import settings

class DriveService:
    def __init__(self, access_token: str, refresh_token: str = None):
        """Initialize Drive service with OAuth token"""
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        self.service = build('drive', 'v3', credentials=creds)
    
    def create_folder(self, folder_name: str, parent_folder_id: str = None):
        """Create folder in Drive"""
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, webViewLink'
            ).execute()
            
            print(f"Created Drive folder: {folder.get('name')} - {folder.get('id')}")
            
            return {
                'id': folder.get('id'),
                'link': folder.get('webViewLink')
            }
        except HttpError as e:
            print(f"Drive folder creation error: {e}")
            return None
    
    def upload_file(self, file_path: str, folder_id: str = None, file_name: str = None):
        """Upload file to Drive"""
        try:
            if not file_name:
                file_name = Path(file_path).name
            
            file_metadata = {'name': file_name}
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            print(f"Uploaded to Drive: {file_name} - {file.get('id')}")
            
            return {
                'id': file.get('id'),
                'view_link': file.get('webViewLink'),
                'download_link': file.get('webContentLink'),
                'name': file_name
            }
        except HttpError as e:
            print(f"Drive upload error: {e}")
            return None
    
    def list_files(self, folder_id: str = None, page_size: int = 10):
        """List files from Drive"""
        try:
            query = ""
            if folder_id:
                query = f"'{folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                fields="files(id, name, webViewLink, createdTime, size)"
            ).execute()
            
            return results.get('files', [])
        except HttpError as e:
            print(f"Drive list error: {e}")
            return []