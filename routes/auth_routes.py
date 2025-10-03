"""
Authentication Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import get_db
from models import User, OTP
from schemas import UserRegister, UserLogin, SendOTP, VerifyOTP, ResetPassword, Token, UserResponse
from auth import get_password_hash, verify_password, create_access_token, generate_otp, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register new user"""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(400, "Email already registered")
    
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        name=user_data.name,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    try:
        from google_drive import create_user_folder
        folder_id = create_user_folder(new_user.email)
        if folder_id:
            new_user.google_drive_folder_id = folder_id
            db.commit()
    except Exception as e:
        print(f"Drive folder creation skipped: {e}")
    
    access_token = create_access_token(data={"sub": new_user.email})
    
    print(f"✅ User registered: {new_user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name
        }
    }

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(403, "Account is disabled")
    
    access_token = create_access_token(data={"sub": user.email})
    
    print(f"✅ User logged in: {user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }

@router.post("/send-otp")
async def send_otp(data: SendOTP, db: Session = Depends(get_db)):
    """Send OTP for password reset"""
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return {"message": "If email exists, OTP has been sent"}
    
    otp_code = generate_otp()
    
    db.query(OTP).filter(OTP.email == data.email, OTP.is_verified == False).delete()
    
    new_otp = OTP(
        email=data.email,
        otp=otp_code,
        purpose="reset_password",
        is_verified=False,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(new_otp)
    db.commit()
    
    print(f"🔐 OTP for {data.email}: {otp_code}")
    
    return {"message": "OTP sent to email", "otp_debug": otp_code}

@router.post("/verify-otp")
async def verify_otp_endpoint(data: VerifyOTP, db: Session = Depends(get_db)):
    """Verify OTP"""
    otp_record = db.query(OTP).filter(
        OTP.email == data.email,
        OTP.otp == data.otp,
        OTP.is_verified == False,
        OTP.expires_at > datetime.utcnow()
    ).first()
    
    if not otp_record:
        raise HTTPException(400, "Invalid or expired OTP")
    
    otp_record.is_verified = True
    db.commit()
    
    return {"message": "OTP verified successfully"}

@router.post("/reset-password")
async def reset_password(data: ResetPassword, db: Session = Depends(get_db)):
    """Reset password using OTP"""
    otp_record = db.query(OTP).filter(
        OTP.email == data.email,
        OTP.otp == data.otp,
        OTP.is_verified == True,
        OTP.expires_at > datetime.utcnow()
    ).first()
    
    if not otp_record:
        raise HTTPException(400, "Invalid or expired OTP")
    
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    user.password_hash = get_password_hash(data.new_password)
    db.commit()
    
    db.delete(otp_record)
    db.commit()
    
    print(f"✅ Password reset: {user.email}")
    
    return {"message": "Password reset successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user