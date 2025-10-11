"""
Authentication Service
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from fastapi import HTTPException
import jwt
from config import settings
from typing import Optional

class AuthService:
    """Handle authentication operations"""
    
    @staticmethod
    async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
        """Get user from JWT token"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            user_id = payload.get("user_id")
            email = payload.get("sub")
            
            if not user_id and not email:
                return None
            
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
            else:
                result = await db.execute(select(User).where(User.email == email))
            
            user = result.scalar_one_or_none()
            
            if user:
                print(f"✅ User found from token: {user.email}")
            
            return user
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            print(f"❌ Token verification error: {str(e)}")
            return None