"""
Subscription API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_db
from models.user import User
from models.subscription import SubscriptionPlan, UserSubscription
from services.subscription_service import SubscriptionService
from services.payment_service import PaymentService
from services.auth_service import AuthService
from pydantic import BaseModel
from typing import List, Optional
import jwt
from config import settings

router = APIRouter(prefix="/api/subscription", tags=["Subscription"])

# Pydantic models for requests
class CreateCheckoutRequest(BaseModel):
    plan_name: str  # "basic" or "pro"

class CancelSubscriptionRequest(BaseModel):
    cancel_at_period_end: bool = True

# Helper function to verify JWT token
def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

async def get_current_user(token: str, db: AsyncSession) -> User:
    """Get current user from token"""
    payload = verify_token(token)
    user_email = payload.get("sub")
    
    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(404, "User not found")
    
    return user

@router.get("/plans")
async def get_subscription_plans(db: AsyncSession = Depends(get_db)):
    """Get all available subscription plans"""
    try:
        plans = await SubscriptionService.get_all_plans(db)
        return {
            "success": True,
            "plans": [plan.to_dict() for plan in plans]
        }
    except Exception as e:
        print(f"❌ Error fetching plans: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-subscription")
async def get_my_subscription(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's subscription details"""
    try:
        # Get user from token
        user = await AuthService.get_user_from_token(token, db)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get subscription with EAGER LOADING
        result = await db.execute(
            select(UserSubscription)
            .options(selectinload(UserSubscription.plan))
            .where(UserSubscription.user_id == user.id)
            .where(UserSubscription.status == 'active')
            .order_by(UserSubscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()
        
        # Get user's current plan
        current_plan = user.current_plan or 'free'
        
        # Get plan details
        plan_result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.name == current_plan)
        )
        plan = plan_result.scalar_one_or_none()
        
        # Build response
        response = {
            "success": True,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "current_plan": current_plan,
                "pdf_count_this_month": user.pdf_count_this_month or 0,
                "pdf_limit": plan.pdf_limit if plan else 5,
                "can_process_pdf": True
            },
            "subscription": None,
            "plan": None
        }
        
        if subscription:
            response["subscription"] = {
                "id": str(subscription.id),
                "status": subscription.status,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "created_at": subscription.created_at.isoformat() if subscription.created_at else None
            }
            
            if subscription.plan:
                response["plan"] = {
                    "id": str(subscription.plan.id),
                    "name": subscription.plan.name,
                    "display_name": subscription.plan.display_name,
                    "price": float(subscription.plan.price),
                    "pdf_limit": subscription.plan.pdf_limit,
                    "description": subscription.plan.description
                }
        
        elif plan:
            # No active subscription, use current plan
            response["plan"] = {
                "id": str(plan.id),
                "name": plan.name,
                "display_name": plan.display_name,
                "price": float(plan.price),
                "pdf_limit": plan.pdf_limit,
                "description": plan.description
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching subscription: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-checkout")
async def create_checkout_session(
    request: CreateCheckoutRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe checkout session for subscription upgrade"""
    try:
        user = await get_current_user(token, db)
        
        # Get plan
        plan = await SubscriptionService.get_plan_by_name(db, request.plan_name)
        if not plan:
            raise HTTPException(404, f"Plan '{request.plan_name}' not found")
        
        if not plan.stripe_price_id:
            raise HTTPException(400, f"Plan '{request.plan_name}' is not configured for payment")
        
        # Create or get Stripe customer
        if not hasattr(user, 'stripe_customer_id') or not user.stripe_customer_id:
            customer = await PaymentService.create_customer(
                email=user.email,
                name=user.name,
                user_id=str(user.id)
            )
            customer_id = customer['id']
            
            # Update user with customer ID
            user.stripe_customer_id = customer_id
            await db.commit()
        else:
            customer_id = user.stripe_customer_id
        
        # Create checkout session
        checkout = await PaymentService.create_checkout_session(
            customer_id=customer_id,
            price_id=plan.stripe_price_id,
            user_id=str(user.id),
            plan_name=plan.name
        )
        
        return {
            "success": True,
            "checkout_url": checkout["url"],
            "session_id": checkout["session_id"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Checkout creation error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel")
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Cancel user's subscription"""
    try:
        user = await get_current_user(token, db)
        
        # Get active subscription
        subscription = await SubscriptionService.get_user_active_subscription(db, str(user.id))
        
        if not subscription:
            raise HTTPException(404, "No active subscription found")
        
        # Cancel in Stripe
        if subscription.stripe_subscription_id:
            await PaymentService.cancel_subscription(subscription.stripe_subscription_id)
        
        # Cancel in database
        subscription = await SubscriptionService.cancel_subscription(
            db, str(user.id), request.cancel_at_period_end
        )
        
        return {
            "success": True,
            "message": "Subscription cancelled successfully",
            "subscription": subscription.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Cancellation error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usage")
async def get_usage_stats(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get user's current usage statistics"""
    try:
        user = await get_current_user(token, db)
        
        # Get user's plan limit
        pdf_limit = getattr(user, 'pdf_limit', 5)
        pdf_count = getattr(user, 'pdf_count_this_month', 0) or 0
        
        percentage = 0
        if pdf_limit > 0:
            percentage = (pdf_count / pdf_limit) * 100
        elif pdf_limit == -1:  # Unlimited
            percentage = 0
        
        # Check if user can process PDF
        can_process = True
        if pdf_limit > 0:
            can_process = pdf_count < pdf_limit
        
        return {
            "success": True,
            "usage": {
                "current_count": pdf_count,
                "limit": pdf_limit,
                "remaining": pdf_limit - pdf_count if pdf_limit > 0 else -1,
                "percentage": round(percentage, 2),
                "can_process": can_process,
                "plan": user.current_plan or 'free'
            }
        }
    
    except Exception as e:
        print(f"❌ Usage stats error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))