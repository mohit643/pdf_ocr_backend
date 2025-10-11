"""
OAuth Authentication Routes
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import uuid

from config import settings
from services.oauth_service import OAuthService
from database import get_db
from models.user import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory user storage (for backward compatibility)
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
async def google_callback(code: str, state: str = None, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        print("=== OAuth Callback Started ===")
        
        # Exchange code for token
        token_data = await oauth_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        token_expiry = token_data.get("expires_in", 3600)
        
        if not access_token:
            raise HTTPException(400, "No access token received")
        
        print(f"✅ Access token received: {access_token[:20]}...")
        print(f"✅ Refresh token: {'Yes' if refresh_token else 'No'}")
        
        # Get user info
        user_info = await oauth_service.get_user_info(access_token)
        user_email = user_info.get("email")
        
        # ✅ CHECK DATABASE FIRST
        result = await db.execute(select(User).where(User.email == user_email))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            # Create Drive folder
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
            
            # ✅ CREATE USER IN DATABASE
            db_user = User(
                email=user_email,
                name=user_info.get("name"),
                picture=user_info.get("picture"),
                google_id=user_info.get("id"),
                google_access_token=access_token,
                google_refresh_token=refresh_token,
                token_expiry=datetime.utcnow() + timedelta(seconds=token_expiry),
                drive_folder_id=drive_folder_id,
                drive_folder_link=drive_folder_link,
                current_plan="free",
                pdf_limit=5,
                pdf_count_this_month=0,
                is_active=True,
                is_verified=True,
                last_login=datetime.utcnow()
            )
            
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
            
            print(f"✅ User created in DATABASE: {user_email} (ID: {db_user.id})")
            
            # Store in memory for backward compatibility
            USERS[user_email] = {
                "id": str(db_user.id),
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
        else:
            # ✅ UPDATE EXISTING USER IN DATABASE
            db_user.google_access_token = access_token
            if refresh_token:
                db_user.google_refresh_token = refresh_token
            db_user.token_expiry = datetime.utcnow() + timedelta(seconds=token_expiry)
            db_user.last_login = datetime.utcnow()
            
            await db.commit()
            
            print(f"✅ User updated in DATABASE: {user_email}")
            
            # Update memory
            USERS[user_email] = {
                "id": str(db_user.id),
                "email": db_user.email,
                "name": db_user.name,
                "picture": db_user.picture,
                "drive_folder_id": db_user.drive_folder_id,
                "drive_folder_link": db_user.drive_folder_link,
                "google_access_token": access_token,
                "google_refresh_token": refresh_token,
                "token_expiry": (datetime.utcnow() + timedelta(seconds=token_expiry)).isoformat(),
                "created_at": db_user.created_at.isoformat() if db_user.created_at else datetime.utcnow().isoformat()
            }
        
        # Create JWT token
        jwt_token = create_access_token({
            "id": str(db_user.id),
            "email": db_user.email,
            "name": db_user.name
        })
        
        # Store session
        SESSIONS[jwt_token] = {
            "user_id": str(db_user.id),
            "email": db_user.email,
            "created_at": datetime.utcnow().isoformat()
        }
        
        print(f"✅ Session created for: {user_email}")
        
        # Redirect to frontend
        frontend_url = f"http://localhost:3000/?token={jwt_token}"
        
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        print(f"❌ OAuth error: {str(e)}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="http://localhost:3000?error=auth_failed")

@router.get("/me")
async def get_current_user(token: str, db: AsyncSession = Depends(get_db)):
    """Get current user info from query param token"""
    try:
        payload = verify_token(token)
        user_email = payload.get("sub")
        
        # Check memory first
        user = USERS.get(user_email)
        
        # If not in memory, load from database
        if not user:
            print(f"⚠️ User not in memory, loading from database: {user_email}")
            result = await db.execute(select(User).where(User.email == user_email))
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                raise HTTPException(404, "User not found")
            
            # Load into memory
            USERS[user_email] = {
                "id": str(db_user.id),
                "email": db_user.email,
                "name": db_user.name,
                "picture": db_user.picture,
                "drive_folder_id": db_user.drive_folder_id,
                "drive_folder_link": db_user.drive_folder_link,
                "google_access_token": db_user.google_access_token,
                "google_refresh_token": db_user.google_refresh_token,
                "token_expiry": db_user.token_expiry.isoformat() if db_user.token_expiry else datetime.utcnow().isoformat(),
                "created_at": db_user.created_at.isoformat() if db_user.created_at else datetime.utcnow().isoformat()
            }
            user = USERS[user_email]
            print(f"✅ User loaded from database into memory")
        
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "picture": user.get("picture"),
            "drive_folder_id": user.get("drive_folder_id"),
            "drive_folder_link": user.get("drive_folder_link")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Get user error: {str(e)}")
        raise HTTPException(401, f"Authentication failed: {str(e)}")

@router.get("/drive-token")
async def get_drive_token(token: str, db: AsyncSession = Depends(get_db)):
    """Get Google Drive access token for authenticated user"""
    try:
        payload = verify_token(token)
        user_email = payload.get("sub")
        
        # Check memory first
        user = USERS.get(user_email)
        
        # If not in memory, load from database
        if not user:
            print(f"⚠️ User not in memory, loading from database: {user_email}")
            result = await db.execute(select(User).where(User.email == user_email))
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                raise HTTPException(404, "User not found")
            
            # Load into memory
            USERS[user_email] = {
                "id": str(db_user.id),
                "email": db_user.email,
                "name": db_user.name,
                "picture": db_user.picture,
                "drive_folder_id": db_user.drive_folder_id,
                "drive_folder_link": db_user.drive_folder_link,
                "google_access_token": db_user.google_access_token,
                "google_refresh_token": db_user.google_refresh_token,
                "token_expiry": db_user.token_expiry.isoformat() if db_user.token_expiry else datetime.utcnow().isoformat(),
                "created_at": db_user.created_at.isoformat() if db_user.created_at else datetime.utcnow().isoformat()
            }
            user = USERS[user_email]
            print(f"✅ User loaded from database into memory")
        
        token_expiry = datetime.fromisoformat(user.get("token_expiry", datetime.utcnow().isoformat()))
        
        if datetime.utcnow() >= token_expiry:
            print(f"⚠️ Token expired for {user_email}, refreshing...")
            
            refresh_token = user.get("google_refresh_token")
            if not refresh_token:
                raise HTTPException(401, "No refresh token available. Please login again.")
            
            try:
                new_token_data = await oauth_service.refresh_access_token(refresh_token)
                new_access_token = new_token_data.get("access_token")
                new_expiry = new_token_data.get("expires_in", 3600)
                
                # Update memory
                USERS[user_email]["google_access_token"] = new_access_token
                USERS[user_email]["token_expiry"] = (
                    datetime.utcnow() + timedelta(seconds=new_expiry)
                ).isoformat()
                
                # Update database
                result = await db.execute(select(User).where(User.email == user_email))
                db_user = result.scalar_one_or_none()
                if db_user:
                    db_user.google_access_token = new_access_token
                    db_user.token_expiry = datetime.utcnow() + timedelta(seconds=new_expiry)
                    await db.commit()
                    print(f"✅ Token updated in database")
                
                print(f"✅ Token refreshed for {user_email}")
                
                return {
                    "access_token": new_access_token,
                    "expires_in": new_expiry,
                    "refreshed": True
                }
                
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                raise HTTPException(401, "Token refresh failed. Please login again.")
        
        return {
            "access_token": user["google_access_token"],
            "expires_in": int((token_expiry - datetime.utcnow()).total_seconds()),
            "refreshed": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Drive token error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to get Drive token: {str(e)}")
    
@router.post("/logout")
async def logout(token: str):
    """Logout user and clear session"""
    try:
        payload = verify_token(token)
        user_email = payload.get("sub")
        
        if token in SESSIONS:
            del SESSIONS[token]
        
        print(f"✅ User logged out: {user_email}")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
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