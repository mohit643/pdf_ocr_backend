"""
Payment & Stripe Webhook Routes
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import get_db
from models.user import User
from models.subscription import SubscriptionPlan
from services.payment_service import PaymentService
from services.subscription_service import SubscriptionService
from datetime import datetime
from typing import Optional, Dict
import stripe

router = APIRouter(prefix="/api/payment", tags=["Payment"])

# Pydantic Models
class PaymentIntentRequest(BaseModel):
    amount: int
    currency: str = "inr"
    user_id: Optional[str] = None
    metadata: Optional[Dict] = None

class VerifyPaymentRequest(BaseModel):
    payment_intent_id: str

@router.post("/create-payment-intent")
async def create_payment_intent(
    request: PaymentIntentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a Payment Intent for one-time payment"""
    try:
        customer_id = None
        
        if request.user_id:
            result = await db.execute(
                select(User).where(User.id == request.user_id)
            )
            user = result.scalar_one_or_none()
            if user and user.stripe_customer_id:
                customer_id = user.stripe_customer_id
        
        payment_data = await PaymentService.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            customer_id=customer_id,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "client_secret": payment_data["client_secret"],
            "payment_intent_id": payment_data["payment_intent_id"]
        }
    
    except Exception as e:
        print(f"❌ Payment Intent creation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-payment")
async def verify_payment(request: VerifyPaymentRequest):
    """Verify if payment was successful"""
    try:
        payment_data = await PaymentService.verify_payment(
            request.payment_intent_id
        )
        
        return {
            "success": True,
            "status": payment_data["status"],
            "amount": payment_data["amount"],
            "currency": payment_data["currency"],
            "metadata": payment_data.get("metadata", {})
        }
    
    except Exception as e:
        print(f"❌ Payment verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook events"""
    payload = await request.body()
    
    # Verify webhook signature
    try:
        event = PaymentService.construct_webhook_event(payload, stripe_signature)
    except HTTPException as e:
        print(f"❌ Webhook signature verification failed")
        raise e
    
    print(f"📨 Webhook received: {event['type']}")
    
    # Handle different event types
    event_type = event['type']
    
    try:
        if event_type == 'payment_intent.succeeded':
            await handle_payment_intent_succeeded(event, db)
        
        elif event_type == 'payment_intent.payment_failed':
            await handle_payment_intent_failed(event, db)
        
        elif event_type == 'checkout.session.completed':
            await handle_checkout_completed(event, db)
        
        elif event_type == 'customer.subscription.updated':
            await handle_subscription_updated(event, db)
        
        elif event_type == 'customer.subscription.deleted':
            await handle_subscription_deleted(event, db)
        
        elif event_type == 'invoice.payment_succeeded':
            await handle_invoice_payment_succeeded(event, db)
        
        elif event_type == 'invoice.payment_failed':
            await handle_invoice_payment_failed(event, db)
        
        else:
            print(f"⚠️ Unhandled webhook event: {event_type}")
    
    except Exception as e:
        print(f"❌ Error handling webhook: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return {"status": "success"}

# Webhook Handlers
async def handle_payment_intent_succeeded(event: dict, db: AsyncSession):
    """Handle successful one-time payment"""
    payment_intent = event['data']['object']
    
    payment_intent_id = payment_intent['id']
    amount = payment_intent['amount']
    metadata = payment_intent.get('metadata', {})
    
    print(f"✅ One-time payment succeeded: {payment_intent_id} - ₹{amount/100}")
    print(f"   Metadata: {metadata}")

async def handle_payment_intent_failed(event: dict, db: AsyncSession):
    """Handle failed one-time payment"""
    payment_intent = event['data']['object']
    
    payment_intent_id = payment_intent['id']
    
    print(f"❌ One-time payment failed: {payment_intent_id}")

async def handle_checkout_completed(event: dict, db: AsyncSession):
    """Handle successful checkout session"""
    session = event['data']['object']
    
    # Get metadata
    user_id = session['metadata'].get('user_id')
    plan_name = session['metadata'].get('plan_name')
    
    if not user_id or not plan_name:
        print(f"⚠️ Missing metadata in checkout session")
        return
    
    # Get subscription ID from session
    stripe_subscription_id = session.get('subscription')
    stripe_customer_id = session.get('customer')
    
    # Get plan
    plan = await SubscriptionService.get_plan_by_name(db, plan_name)
    if not plan:
        print(f"⚠️ Plan not found: {plan_name}")
        return
    
    # Create subscription in database
    subscription = await SubscriptionService.create_subscription(
        db=db,
        user_id=user_id,
        plan_id=plan.id,
        stripe_subscription_id=stripe_subscription_id,
        stripe_customer_id=stripe_customer_id
    )
    
    print(f"✅ Subscription created from checkout: {subscription.id}")

async def handle_subscription_updated(event: dict, db: AsyncSession):
    """Handle subscription update"""
    subscription_data = event['data']['object']
    
    stripe_subscription_id = subscription_data['id']
    status_map = {
        'active': 'active',
        'past_due': 'past_due',
        'canceled': 'cancelled',
        'unpaid': 'unpaid'
    }
    status = status_map.get(subscription_data['status'], 'active')
    
    current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
    
    await SubscriptionService.update_subscription_from_stripe(
        db=db,
        stripe_subscription_id=stripe_subscription_id,
        status=status,
        current_period_end=current_period_end
    )
    
    print(f"✅ Subscription updated: {stripe_subscription_id} - {status}")

async def handle_subscription_deleted(event: dict, db: AsyncSession):
    """Handle subscription deletion"""
    subscription_data = event['data']['object']
    
    stripe_subscription_id = subscription_data['id']
    
    await SubscriptionService.update_subscription_from_stripe(
        db=db,
        stripe_subscription_id=stripe_subscription_id,
        status='cancelled',
        current_period_end=datetime.utcnow()
    )
    
    print(f"✅ Subscription cancelled: {stripe_subscription_id}")

async def handle_invoice_payment_succeeded(event: dict, db: AsyncSession):
    """Handle successful invoice payment"""
    invoice = event['data']['object']
    
    stripe_subscription_id = invoice.get('subscription')
    
    if stripe_subscription_id:
        print(f"✅ Invoice payment succeeded for subscription: {stripe_subscription_id}")

async def handle_invoice_payment_failed(event: dict, db: AsyncSession):
    """Handle failed invoice payment"""
    invoice = event['data']['object']
    
    stripe_subscription_id = invoice.get('subscription')
    
    if stripe_subscription_id:
        await SubscriptionService.update_subscription_from_stripe(
            db=db,
            stripe_subscription_id=stripe_subscription_id,
            status='past_due',
            current_period_end=datetime.utcnow()
        )
        
        print(f"⚠️ Invoice payment failed for subscription: {stripe_subscription_id}")

@router.get("/config")
async def get_payment_config():
    """Get Stripe publishable key for frontend"""
    from config import settings
    
    return {
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY
    }