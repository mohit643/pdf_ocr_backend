"""
OAuth Authentication Routes
"""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import datetime, timedelta
import jwt
import uuid

from config import settings
from services.oauth_service import OAuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory user storage (replace with database if needed later)
USERS = {}
SESSIONS = {}

# Initialize OAuth service
oauth_service = OAuthService(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=settings.GOOGLE_REDIRECT_URI
)

def create_access_token(user_data: dict) -> str:
    """Create JWT access token"""
    payload = {
        "sub": user_data["email"],
        "user_id": user_data["id"],
        "name": user_data["name"],
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    }
    # Use SECRET_KEY instead of JWT_SECRET_KEY
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth login"""
    print("=== Google Login Route Hit ===")
    print(f"Client ID: {settings.GOOGLE_CLIENT_ID[:20]}...")
    print(f"Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
    
    state = str(uuid.uuid4())
    auth_url = oauth_service.get_authorization_url(state=state)
    
    print(f"Auth URL: {auth_url[:100]}...")
    
    return RedirectResponse(url=auth_url)

@router.get("/google/callback")
async def google_callback(code: str, state: str = None):
    """Handle Google OAuth callback"""
    try:
        # Exchange code for token
        token_data = await oauth_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        if not access_token:
            raise HTTPException(400, "No access token received")
        
        # Get user info
        user_info = await oauth_service.get_user_info(access_token)
        user_email = user_info.get("email")
        user_id = USERS.get(user_email, {}).get("id")
        
        if not user_id:
            # Create new user
            user_id = str(uuid.uuid4())
            
            # Create Drive folder for user
            from services.drive_service import DriveService
            drive = DriveService(access_token, refresh_token)
            folder = drive.create_folder(f"PDF_Editor_{user_email.split('@')[0]}")
            
            USERS[user_email] = {
                "id": user_id,
                "email": user_email,
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "drive_folder_id": folder['id'] if folder else None,
                "drive_folder_link": folder['link'] if folder else None,
                "drive_access_token": access_token,
                "drive_refresh_token": refresh_token,
                "created_at": datetime.now().isoformat()
            }
            print(f"New user created with Drive folder: {user_email}")
        else:
            # Update existing user tokens
            USERS[user_email]["drive_access_token"] = access_token
            if refresh_token:
                USERS[user_email]["drive_refresh_token"] = refresh_token
            print(f"Existing user logged in: {user_email}")
        
        # Create JWT token
        jwt_token = create_access_token(USERS[user_email])
        
        # Store session
        SESSIONS[jwt_token] = {
            "user_id": user_id,
            "email": user_email,
            "created_at": datetime.now().isoformat()
        }
        
        # Redirect to frontend
        frontend_url = f"http://localhost:3000?token={jwt_token}"
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        print(f"OAuth error: {str(e)}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="http://localhost:3000?error=auth_failed")
    
@router.get("/me")
async def get_current_user(token: str):
    """Get current user info from token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_email = payload.get("sub")
        
        user = USERS.get(user_email)
        if not user:
            raise HTTPException(404, "User not found")
        
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "picture": user.get("picture")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

@router.post("/logout")
async def logout(token: str):
    """Logout user"""
    if token in SESSIONS:
        del SESSIONS[token]
    
    return {"message": "Logged out successfully"}