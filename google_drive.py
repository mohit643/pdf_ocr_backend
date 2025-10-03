"""
Google Drive Integration - Self-managing folders
No manual folder setup needed
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import os

# ========== CONFIGURATION ==========
SERVICE_ACCOUNT_FILE = 'service-account-key.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
MAIN_FOLDER_NAME = 'PDF_Editor_All_Users'

_drive_service = None
_main_folder_id = None

def get_drive_service():
    """Initialize Google Drive service"""
    global _drive_service
    
    if _drive_service is not None:
        return _drive_service
    
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print(f"❌ Service account file not found: {SERVICE_ACCOUNT_FILE}")
            return None
        
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        
        _drive_service = build('drive', 'v3', credentials=credentials)
        print("✅ Google Drive service initialized")
        return _drive_service
        
    except Exception as e:
        print(f"❌ Failed to initialize Drive: {e}")
        return None


def get_or_create_main_folder():
    """Get or create PDF_Editor_All_Users folder"""
    global _main_folder_id
    
    if _main_folder_id:
        return _main_folder_id
    
    service = get_drive_service()
    if not service:
        return None
    
    try:
        # Search for existing main folder
        query = f"name='{MAIN_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = response.get('files', [])
        
        if folders:
            _main_folder_id = folders[0]['id']
            print(f"📁 Main folder exists: {MAIN_FOLDER_NAME} ({_main_folder_id})")
            return _main_folder_id
        
        # Create main folder
        folder_metadata = {
            'name': MAIN_FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        _main_folder_id = folder.get('id')
        print(f"✅ Created main folder: {MAIN_FOLDER_NAME} ({_main_folder_id})")
        return _main_folder_id
        
    except Exception as e:
        print(f"❌ Error with main folder: {e}")
        return None


def get_or_create_user_folder(user_email: str) -> str:
    """Get or create user folder inside main folder"""
    service = get_drive_service()
    if not service:
        return None
    
    # Ensure main folder exists first
    main_folder_id = get_or_create_main_folder()
    if not main_folder_id:
        return None
    
    try:
        folder_name = user_email.replace('@', '_at_').replace('.', '_')
        
        # Check if user folder exists
        query = f"name='{folder_name}' and '{main_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = response.get('files', [])
        
        if folders:
            folder_id = folders[0]['id']
            print(f"📁 User folder exists: {folder_name}")
            return folder_id
        
        # Create user folder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [main_folder_id]
        }
        
        folder = service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        folder_id = folder.get('id')
        print(f"✅ Created user folder: {folder_name}")
        return folder_id
        
    except Exception as e:
        print(f"❌ Error with user folder: {e}")
        return None


def upload_to_drive(file_path: str, user_email: str, filename: str = None) -> dict:
    """Upload file to user's folder with better error handling"""
    service = get_drive_service()
    if not service:
        return None
    
    try:
        user_folder_id = get_or_create_user_folder(user_email)
        if not user_folder_id:
            return None
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
        
        file_size = os.path.getsize(file_path)
        file_name = filename or os.path.basename(file_path)
        
        print(f"File size: {file_size / 1024:.2f} KB")
        
        file_metadata = {
            'name': file_name,
            'parents': [user_folder_id]
        }
        
        # Use appropriate upload method based on size
        if file_size < 5 * 1024 * 1024:  # Less than 5MB
            media = MediaFileUpload(file_path, mimetype='application/pdf', resumable=False)
        else:
            media = MediaFileUpload(file_path, mimetype='application/pdf', resumable=True, chunksize=1024*1024)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, size',
            supportsAllDrives=True  # Important for shared drive compatibility
        ).execute()
        
        print(f"Uploaded: {file_name}")
        
        return {
            'file_id': file.get('id'),
            'name': file.get('name'),
            'web_view_link': file.get('webViewLink'),
            'size': file.get('size')
        }
        
    except HttpError as error:
        error_details = error.error_details if hasattr(error, 'error_details') else str(error)
        print(f"Drive API Error: {error_details}")
        
        # If quota issue, suggest alternatives
        if 'storageQuotaExceeded' in str(error):
            print("Suggestion: Check if service account has proper permissions or consider using user OAuth instead of service account")
        
        return None
    except Exception as e:
        print(f"Upload error: {e}")
        return None
    
def list_user_files(user_email: str, page_size: int = 10):
    """List files in user's folder"""
    service = get_drive_service()
    if not service:
        return []
    
    try:
        user_folder_id = get_or_create_user_folder(user_email)
        if not user_folder_id:
            return []
        
        query = f"'{user_folder_id}' in parents and trashed=false"
        
        response = service.files().list(
            q=query,
            pageSize=page_size,
            fields='files(id, name, createdTime, size, webViewLink)',
            orderBy='createdTime desc'
        ).execute()
        
        return response.get('files', [])
        
    except Exception as e:
        print(f"❌ Error listing files: {e}")
        return []


if __name__ == "__main__":
    print("Testing Google Drive Integration...")
    
    # Test
    folder_id = get_or_create_user_folder("test@example.com")
    print(f"User folder ID: {folder_id}")