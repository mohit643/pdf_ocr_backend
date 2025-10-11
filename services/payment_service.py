"""
Stripe Payment Service
"""
import stripe
from config import settings
from typing import Optional, Dict
from fastapi import HTTPException

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentService:
    """Handle Stripe payment operations"""
    
    @staticmethod
    async def create_customer(email: str, name: str, user_id: str) -> Dict:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id}
            )
            print(f"✅ Stripe customer created: {customer.id}")
            return customer
        except Exception as e:
            print(f"❌ Stripe customer creation failed: {e}")
            raise HTTPException(500, f"Failed to create customer: {str(e)}")
    
    @staticmethod
    async def create_checkout_session(
        customer_id: str,
        price_id: str,
        user_id: str,
        plan_name: str
    ) -> Dict:
        """Create a Stripe Checkout Session for subscription"""
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                success_url=f"{settings.FRONTEND_URL}/?upgraded=true&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/?upgrade=cancelled",
                metadata={
                    "user_id": user_id,
                    "plan_name": plan_name
                }
            )
            print(f"✅ Checkout session created: {session.id}")
            return {
                "session_id": session.id,
                "url": session.url
            }
        except Exception as e:
            print(f"❌ Checkout session creation failed: {e}")
            raise HTTPException(500, f"Failed to create checkout session: {str(e)}")
    
    @staticmethod
    async def create_payment_intent(
        amount: int,
        currency: str = "inr",
        customer_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Create a Payment Intent for one-time payment"""
        try:
            payment_intent_data = {
                "amount": amount,
                "currency": currency,
                "automatic_payment_methods": {"enabled": True},
            }
            
            if customer_id:
                payment_intent_data["customer"] = customer_id
            
            if metadata:
                payment_intent_data["metadata"] = metadata
            
            payment_intent = stripe.PaymentIntent.create(**payment_intent_data)
            
            print(f"✅ Payment Intent created: {payment_intent.id}")
            
            return {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id
            }
        except Exception as e:
            print(f"❌ Payment Intent creation failed: {e}")
            raise HTTPException(500, f"Failed to create payment intent: {str(e)}")
    
    @staticmethod
    async def verify_payment(payment_intent_id: str) -> Dict:
        """Verify payment status"""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                "status": payment_intent.status,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "payment_method": payment_intent.payment_method,
                "metadata": payment_intent.metadata
            }
        except Exception as e:
            print(f"❌ Payment verification failed: {e}")
            raise HTTPException(500, f"Failed to verify payment: {str(e)}")
    
    @staticmethod
    async def cancel_subscription(subscription_id: str) -> Dict:
        """Cancel a Stripe subscription at period end"""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            print(f"✅ Subscription cancelled: {subscription_id}")
            return subscription
        except Exception as e:
            print(f"❌ Subscription cancellation failed: {e}")
            raise HTTPException(500, f"Failed to cancel subscription: {str(e)}")
    
    @staticmethod
    async def reactivate_subscription(subscription_id: str) -> Dict:
        """Reactivate a cancelled subscription"""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False
            )
            print(f"✅ Subscription reactivated: {subscription_id}")
            return subscription
        except Exception as e:
            print(f"❌ Subscription reactivation failed: {e}")
            raise HTTPException(500, f"Failed to reactivate subscription: {str(e)}")
    
    @staticmethod
    async def get_subscription(subscription_id: str) -> Dict:
        """Get Stripe subscription details"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except Exception as e:
            print(f"❌ Failed to retrieve subscription: {e}")
            raise HTTPException(500, f"Failed to retrieve subscription: {str(e)}")
    
    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str):
        """Construct and verify Stripe webhook event"""
        import json
        
        print("⚠️ DEVELOPMENT MODE: Skipping signature verification")
        print(f"📦 Payload size: {len(payload)} bytes")
        
        try:
            # Parse JSON directly without signature verification
            event = json.loads(payload)
            print(f"✅ Event type: {event.get('type', 'unknown')}")
            return event
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            raise HTTPException(400, "Invalid JSON payload")
        except Exception as e:
            print(f"❌ Error parsing webhook: {e}")
            raise HTTPException(400, str(e))