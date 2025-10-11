"""
Subscription Business Logic Service
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from models.subscription import SubscriptionPlan, UserSubscription
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException

class SubscriptionService:
    """Handle subscription business logic"""
    
    @staticmethod
    async def get_or_create_plan(
        db: AsyncSession,
        name: str,
        display_name: str,
        price: float,
        pdf_limit: int,
        description: str = None,
        stripe_price_id: str = None
    ) -> SubscriptionPlan:
        """Get existing plan or create new one"""
        try:
            result = await db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.name == name)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                plan = SubscriptionPlan(
                    name=name,
                    display_name=display_name,
                    description=description,
                    price=price,
                    pdf_limit=pdf_limit,
                    stripe_price_id=stripe_price_id
                )
                db.add(plan)
                await db.commit()
                await db.refresh(plan)
                print(f"✅ Plan created: {name}")
            
            return plan
        
        except Exception as e:
            print(f"❌ Error in get_or_create_plan: {str(e)}")
            await db.rollback()
            raise
    
    @staticmethod
    async def get_all_plans(db: AsyncSession) -> List[SubscriptionPlan]:
        """Get all subscription plans"""
        try:
            result = await db.execute(
                select(SubscriptionPlan).order_by(SubscriptionPlan.price)
            )
            plans = result.scalars().all()
            print(f"✅ Found {len(plans)} plans")
            return plans
        
        except Exception as e:
            print(f"❌ Error fetching plans: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    async def get_plan_by_name(db: AsyncSession, name: str) -> Optional[SubscriptionPlan]:
        """Get plan by name"""
        try:
            result = await db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.name == name)
            )
            return result.scalar_one_or_none()
        
        except Exception as e:
            print(f"❌ Error fetching plan by name: {str(e)}")
            return None
    
    @staticmethod
    async def get_user_active_subscription(
        db: AsyncSession,
        user_id: str
    ) -> Optional[UserSubscription]:
        """Get user's active subscription"""
        try:
            result = await db.execute(
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status == "active"
                )
                .order_by(UserSubscription.created_at.desc())
            )
            return result.scalar_one_or_none()
        
        except Exception as e:
            print(f"❌ Error fetching active subscription: {str(e)}")
            return None
    
    @staticmethod
    async def create_subscription(
        db: AsyncSession,
        user_id: str,
        plan_id: str,
        stripe_subscription_id: str = None,
        stripe_customer_id: str = None
    ) -> UserSubscription:
        """Create new subscription for user"""
        try:
            # Check if user already has active subscription
            existing = await SubscriptionService.get_user_active_subscription(db, user_id)
            if existing:
                # Cancel existing subscription
                existing.status = "cancelled"
                existing.end_date = datetime.utcnow()
                existing.cancelled_at = datetime.utcnow()
                print(f"⚠️ Cancelled existing subscription for user: {user_id}")
            
            # Create new subscription
            subscription = UserSubscription(
                user_id=user_id,
                plan_id=plan_id,
                stripe_subscription_id=stripe_subscription_id,
                stripe_customer_id=stripe_customer_id,
                status="active",
                start_date=datetime.utcnow(),
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30)
            )
            
            db.add(subscription)
            
            # Update user's current plan
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if user:
                # Get plan details
                result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
                plan = result.scalar_one_or_none()
                
                if plan:
                    user.current_plan = plan.name
                    user.pdf_limit = plan.pdf_limit
                    user.pdf_count_this_month = 0  # Reset count on new subscription
                    print(f"✅ User plan updated: {plan.name}")
            
            await db.commit()
            await db.refresh(subscription)
            
            print(f"✅ Subscription created for user: {user_id}")
            return subscription
        
        except Exception as e:
            print(f"❌ Error creating subscription: {str(e)}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise
    
    @staticmethod
    async def cancel_subscription(
        db: AsyncSession,
        user_id: str,
        cancel_at_period_end: bool = True
    ) -> UserSubscription:
        """Cancel user's subscription"""
        try:
            subscription = await SubscriptionService.get_user_active_subscription(db, user_id)
            
            if not subscription:
                raise HTTPException(404, "No active subscription found")
            
            subscription.cancel_at_period_end = cancel_at_period_end
            subscription.cancelled_at = datetime.utcnow()
            
            if not cancel_at_period_end:
                subscription.status = "cancelled"
                subscription.end_date = datetime.utcnow()
                
                # Downgrade user to free plan
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    user.current_plan = "free"
                    user.pdf_limit = 5
                    print(f"✅ User downgraded to free plan")
            
            await db.commit()
            await db.refresh(subscription)
            
            print(f"✅ Subscription cancelled for user: {user_id}")
            return subscription
        
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error cancelling subscription: {str(e)}")
            await db.rollback()
            raise HTTPException(500, str(e))
    
    @staticmethod
    async def update_subscription_from_stripe(
        db: AsyncSession,
        stripe_subscription_id: str,
        status: str,
        current_period_end: datetime
    ):
        """Update subscription based on Stripe webhook"""
        try:
            result = await db.execute(
                select(UserSubscription).where(
                    UserSubscription.stripe_subscription_id == stripe_subscription_id
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                print(f"⚠️ Subscription not found for Stripe ID: {stripe_subscription_id}")
                return
            
            subscription.status = status
            subscription.current_period_end = current_period_end
            
            # If subscription cancelled/expired, downgrade user
            if status in ["cancelled", "expired", "unpaid"]:
                result = await db.execute(
                    select(User).where(User.id == subscription.user_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    user.current_plan = "free"
                    user.pdf_limit = 5
                    print(f"✅ User downgraded to free plan due to status: {status}")
            
            await db.commit()
            print(f"✅ Subscription updated from webhook: {stripe_subscription_id} - Status: {status}")
        
        except Exception as e:
            print(f"❌ Error updating subscription from webhook: {str(e)}")
            import traceback
            traceback.print_exc()
            await db.rollback()