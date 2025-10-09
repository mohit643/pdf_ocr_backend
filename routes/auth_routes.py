"""
OAuth Authentication Routes
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
import jwt
import uuid

from config import settings
from services.oauth_service import OAuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory user storage (replace with database if needed later)
USERS = {}
SESSIONS = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/google/login")

# Initialize OAuth service with Drive scope
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
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

@router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth login with Drive access"""
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
        print("=== OAuth Callback Started ===")
        
        # Exchange code for token
        token_data = await oauth_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        token_expiry = token_data.get("expires_in", 3600)  # Default 1 hour
        
        if not access_token:
            raise HTTPException(400, "No access token received")
        
        print(f"✅ Access token received: {access_token[:20]}...")
        print(f"✅ Refresh token: {'Yes' if refresh_token else 'No'}")
        
        # Get user info
        user_info = await oauth_service.get_user_info(access_token)
        user_email = user_info.get("email")
        user_id = USERS.get(user_email, {}).get("id")
        
        if not user_id:
            # Create new user
            user_id = str(uuid.uuid4())
            
            # Create Drive folder for user
            try:
                from services.drive_service import DriveService
                drive = DriveService(access_token, refresh_token)
                folder = drive.create_folder(f"PDF_Editor_{user_email.split('@')[0]}")
                
                drive_folder_id = folder['id'] if folder else None
                drive_folder_link = folder['link'] if folder else None
                
                print(f"✅ Drive folder created: {drive_folder_id}")
            except Exception as e:
                print(f"⚠️ Drive folder creation failed: {e}")
                drive_folder_id = None
                drive_folder_link = None
            
            USERS[user_email] = {
                "id": user_id,
                "email": user_email,
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "drive_folder_id": drive_folder_id,
                "drive_folder_link": drive_folder_link,
                "google_access_token": access_token,
                "google_refresh_token": refresh_token,
                "token_expiry": (datetime.utcnow() + timedelta(seconds=token_expiry)).isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            print(f"✅ New user created: {user_email}")
        else:
            # Update existing user tokens
            USERS[user_email]["google_access_token"] = access_token
            if refresh_token:
                USERS[user_email]["google_refresh_token"] = refresh_token
            USERS[user_email]["token_expiry"] = (datetime.utcnow() + timedelta(seconds=token_expiry)).isoformat()
            print(f"✅ Existing user tokens updated: {user_email}")
        
        # Create JWT token
        jwt_token = create_access_token(USERS[user_email])
        
        # Store session
        SESSIONS[jwt_token] = {
            "user_id": user_id,
            "email": user_email,
            "created_at": datetime.utcnow().isoformat()
        }
        
        print(f"✅ Session created for: {user_email}")
        
        # Redirect to frontend
        frontend_url = f"http://localhost:3000/?token={jwt_token}"
        # frontend_url = f"https://document-read-production.up.railway.app/?token={jwt_token}"
        
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        print(f"❌ OAuth error: {str(e)}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="http://localhost:3000?error=auth_failed")

@router.get("/me")
async def get_current_user(token: str):
    """Get current user info from query param token"""
    try:
        payload = verify_token(token)
        user_email = payload.get("sub")
        
        user = USERS.get(user_email)
        if not user:
            raise HTTPException(404, "User not found")
        
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "picture": user.get("picture"),
            "drive_folder_id": user.get("drive_folder_id"),
            "drive_folder_link": user.get("drive_folder_link")
        }
    except Exception as e:
        raise HTTPException(401, f"Authentication failed: {str(e)}")

@router.get("/drive-token")
async def get_drive_token(token: str):
    """Get Google Drive access token for authenticated user"""
    try:
        # Verify JWT token
        payload = verify_token(token)
        user_email = payload.get("sub")
        
        user = USERS.get(user_email)
        if not user:
            raise HTTPException(404, "User not found")
        
        # Check if token is expired
        token_expiry = datetime.fromisoformat(user.get("token_expiry", datetime.utcnow().isoformat()))
        
        if datetime.utcnow() >= token_expiry:
            print(f"⚠️ Token expired for {user_email}, refreshing...")
            
            # Refresh token
            refresh_token = user.get("google_refresh_token")
            if not refresh_token:
                raise HTTPException(401, "No refresh token available. Please login again.")
            
            try:
                # Refresh the access token
                new_token_data = await oauth_service.refresh_access_token(refresh_token)
                new_access_token = new_token_data.get("access_token")
                new_expiry = new_token_data.get("expires_in", 3600)
                
                # Update user data
                USERS[user_email]["google_access_token"] = new_access_token
                USERS[user_email]["token_expiry"] = (
                    datetime.utcnow() + timedelta(seconds=new_expiry)
                ).isoformat()
                
                print(f"✅ Token refreshed for {user_email}")
                
                return {
                    "access_token": new_access_token,
                    "expires_in": new_expiry,
                    "refreshed": True
                }
                
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                raise HTTPException(401, "Token refresh failed. Please login again.")
        
        # Token is still valid
        return {
            "access_token": user["google_access_token"],
            "expires_in": int((token_expiry - datetime.utcnow()).total_seconds()),
            "refreshed": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Drive token error: {e}")
        raise HTTPException(500, f"Failed to get Drive token: {str(e)}")

@router.post("/logout")
async def logout(token: str):
    """Logout user and clear session"""
    try:
        # Verify token
        payload = verify_token(token)
        user_email = payload.get("sub")
        
        # Remove session
        if token in SESSIONS:
            del SESSIONS[token]
        
        print(f"✅ User logged out: {user_email}")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        # Even if token is invalid, still return success
        return {"message": "Logged out successfully"}

@router.get("/validate")
async def validate_token(token: str):
    """Validate JWT token"""
    try:
        payload = verify_token(token)
        user_email = payload.get("sub")
        
        if user_email not in USERS:
            raise HTTPException(404, "User not found")
        
        return {
            "valid": True,
            "email": user_email,
            "user_id": payload.get("user_id"),
            "name": payload.get("name")
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(401, "Invalid token")