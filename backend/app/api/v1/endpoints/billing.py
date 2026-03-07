"""
Billing endpoints for Razorpay Subscriptions API.
Implements lazy quota reset and subscription management.
Uses existing Subscription model from organization.py.
"""

import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User, SubscriptionTier
from app.models.organization import Subscription, SubscriptionStatus, PlanType
from app.api.v1.endpoints.auth import get_current_user
from app.api.dependencies import require_admin
from app.core.config import settings


router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    documents_used: int
    documents_limit: int
    current_period_end: Optional[str]
    razorpay_subscription_id: Optional[str]


class CreateSubscriptionRequest(BaseModel):
    plan_id: str  # Razorpay plan ID


class VerifyPaymentRequest(BaseModel):
    razorpay_subscription_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class InvoiceResponse(BaseModel):
    id: str
    amount: int
    currency: str
    status: str
    plan: str
    created_at: str
    paid_at: Optional[str]


class PlanInfo(BaseModel):
    id: str
    name: str
    price: int  # In paise
    currency: str
    documents_limit: int
    features: List[str]


# ============================================================================
# Quota Helpers
# ============================================================================

def get_plan_limit(plan: str) -> int:
    """Get document limit for a plan."""
    limits = {
        "free": settings.FREE_TIER_SCANS,
        "pro": settings.PRO_TIER_SCANS,
        "enterprise": settings.ENTERPRISE_INCLUDED_SCANS,
    }
    return limits.get(plan.lower(), 5)


async def get_user_subscription(user: User, db: AsyncSession) -> Optional[Subscription]:
    """Get user's organization subscription."""
    if not user.organization_id:
        return None
    
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == user.organization_id)
    )
    return result.scalar_one_or_none()


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's subscription status."""
    subscription = await get_user_subscription(current_user, db)
    
    # Use user tier if no org subscription
    plan = subscription.plan.value if subscription else current_user.subscription_tier.value
    used = subscription.used_scans if subscription else 0
    limit = get_plan_limit(plan)
    
    # Lazy reset: check if 30 days passed
    if subscription and subscription.current_period_end:
        if datetime.utcnow() > subscription.current_period_end:
            subscription.used_scans = 0
            subscription.current_period_start = datetime.utcnow()
            subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
            await db.commit()
            used = 0
    
    return SubscriptionResponse(
        plan=plan,
        status=subscription.status.value if subscription else "active",
        documents_used=used,
        documents_limit=limit if limit > 0 else -1,  # -1 = unlimited
        current_period_end=subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None,
        razorpay_subscription_id=subscription.razorpay_subscription_id if subscription else None,
    )


@router.get("/plans", response_model=List[PlanInfo])
async def list_plans():
    """List available subscription plans."""
    return [
        PlanInfo(
            id="plan_free",
            name="Free",
            price=0,
            currency="INR",
            documents_limit=5,
            features=["Basic clause detection", "5 documents/month", "Community support"],
        ),
        PlanInfo(
            id="plan_pro",  # Replace with actual Razorpay plan ID
            name="Pro",
            price=410000,  # ₹4,100 in paise
            currency="INR",
            documents_limit=-1,  # Unlimited
            features=["All clause detection", "Unlimited documents", "Custom playbooks", "Priority support"],
        ),
        PlanInfo(
            id="plan_enterprise",  # Replace with actual Razorpay plan ID
            name="Enterprise",
            price=1650000,  # ₹16,500 in paise
            currency="INR",
            documents_limit=-1,  # Unlimited
            features=["Everything in Pro", "Custom integrations", "SLA guarantee", "Dedicated account manager"],
        ),
    ]


@router.post("/create-subscription")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Razorpay subscription for upgrading.
    Returns subscription ID for frontend to complete checkout.
    """
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Razorpay not configured. Contact support to upgrade."
        )
    
    try:
        import razorpay
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Create Razorpay customer
        customer = client.customer.create({
            "name": current_user.name,
            "email": current_user.email,
        })
        
        # Create subscription
        razorpay_subscription = client.subscription.create({
            "plan_id": request.plan_id,
            "customer_id": customer['id'],
            "total_count": 12,  # 12 billing cycles
            "customer_notify": 1,
        })
        
        return {
            "subscription_id": razorpay_subscription['id'],
            "short_url": razorpay_subscription.get('short_url'),
            "status": razorpay_subscription['status'],
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify")
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify Razorpay payment signature and activate subscription.
    """
    if not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay not configured")
    
    # Verify signature (timing-safe comparison)
    message = f"{request.razorpay_payment_id}|{request.razorpay_subscription_id}"
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(request.razorpay_signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Determine tier from subscription plan (look up via Razorpay or org subscription)
    subscription = await get_user_subscription(current_user, db)
    if subscription and subscription.plan == PlanType.ENTERPRISE:
        current_user.subscription_tier = SubscriptionTier.ENTERPRISE
        plan_name = "enterprise"
    else:
        current_user.subscription_tier = SubscriptionTier.PRO
        plan_name = "pro"
    await db.commit()

    return {"status": "success", "plan": plan_name}


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's payment history (placeholder - no Invoice table yet)."""
    return []


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Razorpay webhook events."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    if not signature or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Verify webhook signature
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    import json
    event = json.loads(body)
    event_type = event.get("event")
    
    if event_type == "subscription.charged":
        subscription_id = event["payload"]["subscription"]["entity"]["id"]
        result = await db.execute(
            select(Subscription).where(Subscription.razorpay_subscription_id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.used_scans = 0
            subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
            await db.commit()
    
    elif event_type == "subscription.cancelled":
        subscription_id = event["payload"]["subscription"]["entity"]["id"]
        result = await db.execute(
            select(Subscription).where(Subscription.razorpay_subscription_id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED
            await db.commit()
    
    return {"status": "ok"}


# ============================================================================
# Quota Check Dependency (for use in document analysis)
# ============================================================================

async def check_and_increment_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if user has quota remaining and increment usage.
    Use as dependency in document analysis endpoint.
    """
    subscription = await get_user_subscription(current_user, db)
    
    plan = subscription.plan.value if subscription else current_user.subscription_tier.value
    used = subscription.used_scans if subscription else 0
    limit = get_plan_limit(plan)
    
    # Check quota (skip if unlimited = -1)
    if limit > 0 and used >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"Quota exceeded. You've used {used}/{limit} documents this month. Please upgrade."
        )
    
    # Increment usage
    if subscription:
        subscription.used_scans += 1
        await db.commit()
    
    return {"plan": plan, "used": used + 1, "limit": limit}
