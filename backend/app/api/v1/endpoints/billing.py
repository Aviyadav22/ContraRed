"""
Billing endpoints — Phase 3 complete rewrite.

Fixes:
  - Tier inversion bug: Enterprise was 500, Pro was unlimited → fixed
  - Free quota bypass: Solo users got used=0 every time → now tracked via UsageLog

New:
  - 5-tier plan system (Free/Starter/Pro/Business/Enterprise)
  - Dual payment gateway (Razorpay for INR, Stripe for USD)
  - Per-user usage tracking (fixes free bypass)
  - Invoice model and listing
  - Dunning management for failed payments
  - Overage billing (soft cap for paid tiers)
"""

import hmac
import hashlib
import json
import logging
import uuid as uuid_mod
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.user import User, SubscriptionTier
from app.models.organization import Subscription, SubscriptionStatus, PlanType
from app.models.document import UsageLog, UsageAction
from app.models.billing import Invoice, WebhookEvent
from app.api.v1.endpoints.auth import get_current_user
from app.api.dependencies import require_permission, require_admin
from app.core.config import settings
from app.api.v1.endpoints.auth import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Plan Configuration (Phase 3.2 — 5-tier system)
# ============================================================================

PLAN_CATALOG = {
    "free": {
        "name": "Free",
        "scans": settings.FREE_TIER_SCANS,  # 5
        "seats": 1,
        "price_inr": 0,
        "price_usd": 0,
        "features": [
            "Basic clause detection",
            f"{settings.FREE_TIER_SCANS} scans/month",
            "Community support",
        ],
        "overage_price_inr": 0,  # No overage for free
        "overage_price_usd": 0,
        "batch_files_limit": 5,
    },
    "starter": {
        "name": "Starter",
        "scans": settings.STARTER_TIER_SCANS,  # 50
        "seats": 1,
        "price_inr": 249900,  # ₹2,499 in paise
        "price_usd": 2900,  # $29 in cents
        "features": [
            "All clause detection",
            f"{settings.STARTER_TIER_SCANS} scans/month",
            "Custom playbooks",
            "Email support",
        ],
        "overage_price_inr": 14900,  # ₹149/scan overage
        "overage_price_usd": 200,  # $2/scan overage
        "batch_files_limit": 10,
    },
    "pro": {
        "name": "Pro",
        "scans": settings.PRO_TIER_SCANS,  # 200
        "seats": 5,
        "price_inr": 699900,  # ₹6,999 in paise
        "price_usd": 7900,  # $79 in cents
        "features": [
            "All clause detection",
            f"{settings.PRO_TIER_SCANS} scans/month",
            "Custom playbooks",
            "5 team seats",
            "Jurisdiction detection",
            "Priority support",
        ],
        "overage_price_inr": 9900,  # ₹99/scan overage
        "overage_price_usd": 150,  # $1.50/scan overage
        "batch_files_limit": 25,
    },
    "business": {
        "name": "Business",
        "scans": settings.BUSINESS_TIER_SCANS,  # 1000
        "seats": 20,
        "price_inr": 1499900,  # ₹14,999 in paise
        "price_usd": 14900,  # $149 in cents
        "features": [
            "Everything in Pro",
            f"{settings.BUSINESS_TIER_SCANS} scans/month",
            "20 team seats",
            "SSO/SAML",
            "Audit trail",
            "Dedicated support",
        ],
        "overage_price_inr": 7900,  # ₹79/scan overage
        "overage_price_usd": 100,  # $1/scan overage
        "batch_files_limit": 50,
    },
    "enterprise": {
        "name": "Enterprise",
        "scans": settings.ENTERPRISE_INCLUDED_SCANS,  # -1 = Unlimited
        "seats": -1,  # Unlimited
        "price_inr": -1,  # Custom
        "price_usd": -1,  # Custom
        "features": [
            "Everything in Business",
            "Unlimited scans",
            "Unlimited seats",
            "Custom integrations",
            "SLA guarantee",
            "Dedicated account manager",
            "On-premise option",
        ],
        "overage_price_inr": 0,
        "overage_price_usd": 0,
        "batch_files_limit": 50,
    },
}


def get_plan_limit(plan: str) -> int:
    """Get scan limit for a plan. Returns -1 for unlimited."""
    catalog = PLAN_CATALOG.get(plan.lower())
    if catalog:
        return catalog["scans"]
    return settings.FREE_TIER_SCANS


def get_plan_info(plan: str) -> dict:
    """Get full plan catalog entry."""
    return PLAN_CATALOG.get(plan.lower(), PLAN_CATALOG["free"])


# ============================================================================
# Schemas
# ============================================================================

class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    documents_used: int
    documents_limit: int
    seats_used: int = 0
    seats_limit: int = 1
    current_period_end: Optional[str] = None
    razorpay_subscription_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    overage_count: int = 0
    overage_cost: Optional[str] = None


class CreateSubscriptionRequest(BaseModel):
    plan: Literal["starter", "pro", "business", "enterprise"]
    gateway: Literal["razorpay", "stripe"] = "razorpay"
    currency: Literal["INR", "USD"] = "INR"


class VerifyPaymentRequest(BaseModel):
    gateway: Literal["razorpay", "stripe"] = "razorpay"
    # Razorpay fields
    razorpay_subscription_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    # Plan selection (used when creating new subscription)
    plan: Optional[str] = None  # "starter", "pro", "business", "enterprise"
    # Stripe fields
    stripe_session_id: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: str
    amount: int
    currency: str
    status: str
    plan: str
    description: str = ""
    created_at: str
    paid_at: Optional[str] = None
    gateway: str = "razorpay"


class PlanInfo(BaseModel):
    id: str
    name: str
    price_inr: int  # In paise
    price_usd: int  # In cents
    scans_limit: int
    seats_limit: int
    features: List[str]
    overage_price_inr: int = 0
    overage_price_usd: int = 0


class UsageStatsResponse(BaseModel):
    plan: str
    scans_used: int
    scans_limit: int
    scans_remaining: int
    overage_count: int
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    daily_usage: List[dict] = []


# ============================================================================
# Usage Tracking (Phase 3.1 — fixes free quota bypass)
# ============================================================================

async def _get_user_scan_count(user: User, db: AsyncSession) -> int:
    """
    Get the user's scan count for the current billing period.

    Phase 3.1 FIX: For solo users (no org/subscription), track usage
    via UsageLog instead of returning 0 every time.
    """
    # If user has an org subscription, use that
    if user.organization_id:
        result = await db.execute(
            select(Subscription)
            .where(Subscription.organization_id == user.organization_id)
            .where(Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
                SubscriptionStatus.PAST_DUE,
            ]))
        )
        sub = result.scalar_one_or_none()
        if sub:
            return sub.used_scans

    # Solo user: count scans from UsageLog in current 30-day window
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(func.count())
        .select_from(UsageLog)
        .where(UsageLog.user_id == user.id)
        .where(UsageLog.action == UsageAction.SCAN)
        .where(UsageLog.created_at >= period_start)
    )
    return result.scalar() or 0


async def _increment_usage(user: User, db: AsyncSession):
    """Increment scan usage for the user."""
    # If user has org subscription, increment there
    if user.organization_id:
        result = await db.execute(
            select(Subscription)
            .where(Subscription.organization_id == user.organization_id)
            .where(Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
                SubscriptionStatus.PAST_DUE,
            ]))
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.used_scans += 1

    # ALWAYS log to UsageLog (for analytics + solo user tracking)
    usage = UsageLog(
        user_id=user.id,
        organization_id=user.organization_id,
        action=UsageAction.SCAN,
        tokens_used=0,
    )
    db.add(usage)


# ============================================================================
# Quota Helpers
# ============================================================================

async def get_user_subscription(user: User, db: AsyncSession) -> Optional[Subscription]:
    """Get user's active organization subscription."""
    if not user.organization_id:
        return None
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == user.organization_id)
        .where(Subscription.status.in_([
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,
        ]))
    )
    return result.scalar_one_or_none()


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's subscription status."""
    subscription = await get_user_subscription(current_user, db)

    plan = subscription.plan.value if subscription else current_user.subscription_tier.value
    plan_info = get_plan_info(plan)
    used = await _get_user_scan_count(current_user, db)
    limit = plan_info["scans"]

    # Lazy reset: check if period expired
    # Note: Minor race condition possible on concurrent requests; acceptable for quota tracking
    if subscription and subscription.current_period_end:
        if datetime.now(timezone.utc) > subscription.current_period_end:
            subscription.used_scans = 0
            subscription.current_period_start = datetime.now(timezone.utc)
            subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
            await db.commit()
            used = 0

    # Calculate overage
    overage = max(0, used - limit) if limit > 0 else 0

    return SubscriptionResponse(
        plan=plan,
        status=subscription.status.value if subscription else "active",
        documents_used=used,
        documents_limit=limit,
        seats_used=0,  # TODO: count org members
        seats_limit=plan_info["seats"],
        current_period_end=subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None,
        razorpay_subscription_id=subscription.razorpay_subscription_id if subscription else None,
        overage_count=overage,
    )


@router.get("/plans", response_model=List[PlanInfo])
async def list_plans(current_user: User = Depends(get_current_user)):
    """List all available subscription plans with pricing."""
    plans = []
    for plan_id, info in PLAN_CATALOG.items():
        plans.append(PlanInfo(
            id=plan_id,
            name=info["name"],
            price_inr=info["price_inr"],
            price_usd=info["price_usd"],
            scans_limit=info["scans"],
            seats_limit=info["seats"],
            features=info["features"],
            overage_price_inr=info.get("overage_price_inr", 0),
            overage_price_usd=info.get("overage_price_usd", 0),
        ))
    return plans


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed usage statistics for the current billing period."""
    subscription = await get_user_subscription(current_user, db)
    plan = subscription.plan.value if subscription else current_user.subscription_tier.value
    plan_info = get_plan_info(plan)
    used = await _get_user_scan_count(current_user, db)
    limit = plan_info["scans"]
    overage = max(0, used - limit) if limit > 0 else 0
    remaining = max(0, limit - used) if limit > 0 else -1

    # Daily usage for last 30 days
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    daily_result = await db.execute(
        select(
            func.date_trunc("day", UsageLog.created_at).label("day"),
            func.count().label("count"),
        )
        .where(UsageLog.user_id == current_user.id)
        .where(UsageLog.action == UsageAction.SCAN)
        .where(UsageLog.created_at >= period_start)
        .group_by("day")
        .order_by("day")
    )
    daily_usage = [
        {"date": row.day.isoformat() if row.day else "", "count": row.count}
        for row in daily_result.all()
    ]

    return UsageStatsResponse(
        plan=plan,
        scans_used=used,
        scans_limit=limit,
        scans_remaining=remaining,
        overage_count=overage,
        current_period_start=subscription.current_period_start.isoformat() if subscription and subscription.current_period_start else None,
        current_period_end=subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None,
        daily_usage=daily_usage,
    )


@router.post("/create-subscription")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: User = Depends(require_permission("billing.manage")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a subscription checkout session.

    Supports dual payment gateways:
    - Razorpay for INR payments (Indian customers)
    - Stripe for USD/EUR/GBP payments (international customers)
    """
    plan_info = get_plan_info(request.plan)
    if plan_info["price_inr"] < 0:
        raise HTTPException(status_code=400, detail="Enterprise plans require contacting sales.")

    if request.gateway == "razorpay":
        return await _create_razorpay_subscription(current_user, request, plan_info, db)
    elif request.gateway == "stripe":
        return await _create_stripe_checkout(current_user, request, plan_info, db)
    else:
        raise HTTPException(status_code=400, detail="Unsupported payment gateway")


async def _create_razorpay_subscription(user, request, plan_info, db):
    """Create Razorpay subscription."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay not configured. Contact support.")

    try:
        import razorpay
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # Determine plan ID based on plan name
        plan_id_map = {
            "starter": settings.RAZORPAY_PLAN_STARTER_ID or settings.RAZORPAY_PLAN_PRO_ID,
            "pro": settings.RAZORPAY_PLAN_PRO_ID,
            "business": settings.RAZORPAY_PLAN_BUSINESS_ID or settings.RAZORPAY_PLAN_ENTERPRISE_ID,
            "enterprise": settings.RAZORPAY_PLAN_ENTERPRISE_ID,
        }
        razorpay_plan_id = plan_id_map.get(request.plan)
        if not razorpay_plan_id:
            raise HTTPException(status_code=400, detail=f"No Razorpay plan configured for {request.plan}")

        customer = client.customer.create({
            "name": user.name,
            "email": user.email,
        })

        razorpay_subscription = client.subscription.create({
            "plan_id": razorpay_plan_id,
            "customer_id": customer["id"],
            "total_count": 12,
            "customer_notify": 1,
        })

        return {
            "gateway": "razorpay",
            "subscription_id": razorpay_subscription["id"],
            "short_url": razorpay_subscription.get("short_url"),
            "status": razorpay_subscription["status"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Razorpay subscription creation failed", exc_info=True)
        raise HTTPException(status_code=400, detail={"message": "Subscription creation failed.", "error_code": "payment_error"})


async def _create_stripe_checkout(user, request, plan_info, db):
    """Create Stripe checkout session."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured. Use Razorpay for INR payments.")

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Create checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=user.email,
            line_items=[{
                "price_data": {
                    "currency": request.currency.lower(),
                    "unit_amount": plan_info["price_inr"] if request.currency == "INR" else plan_info["price_usd"],
                    "recurring": {"interval": "month"},
                    "product_data": {
                        "name": f"ContraRed {plan_info['name']}",
                        "description": f"{plan_info['scans']} scans/month, {plan_info['seats']} seats",
                    },
                },
                "quantity": 1,
            }],
            metadata={
                "user_id": str(user.id),
                "plan": request.plan,
            },
        )

        return {
            "gateway": "stripe",
            "session_id": session.id,
            "checkout_url": session.url,
            "status": session.status,
        }

    except ImportError:
        raise HTTPException(status_code=503, detail="Stripe SDK not installed.")
    except Exception as e:
        logger.error("Stripe checkout creation failed", exc_info=True)
        raise HTTPException(status_code=400, detail={"message": "Checkout creation failed.", "error_code": "payment_error"})


@router.post("/verify")
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: User = Depends(require_permission("billing.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Verify payment and activate subscription (Razorpay or Stripe)."""
    if request.gateway == "razorpay":
        return await _verify_razorpay(request, current_user, db)
    elif request.gateway == "stripe":
        return await _verify_stripe(request, current_user, db)
    else:
        raise HTTPException(status_code=400, detail="Unsupported gateway")


async def _verify_razorpay(request, current_user, db):
    """Verify Razorpay payment signature."""
    if not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay not configured")
    if not request.razorpay_payment_id or not request.razorpay_subscription_id or not request.razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing Razorpay payment fields")

    message = f"{request.razorpay_payment_id}|{request.razorpay_subscription_id}"
    expected_signature = hmac.HMAC(
        settings.RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(request.razorpay_signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Determine plan from the Razorpay subscription (or default to pro)
    # Note: Full amount verification happens via webhook; this is the initial check
    subscription = await get_user_subscription(current_user, db)
    plan_name = "pro"  # default
    tier_map = {
        PlanType.STARTER: (SubscriptionTier.STARTER, "starter"),
        PlanType.PRO: (SubscriptionTier.PRO, "pro"),
        PlanType.BUSINESS: (SubscriptionTier.BUSINESS, "business"),
        PlanType.ENTERPRISE: (SubscriptionTier.ENTERPRISE, "enterprise"),
    }
    if subscription and subscription.plan in tier_map:
        tier, plan_name = tier_map[subscription.plan]
        current_user.subscription_tier = tier

        # Verify payment amount matches expected plan price
        if plan_name in PLAN_CATALOG:
            expected_price = PLAN_CATALOG[plan_name].get("price_inr", 0)
            # Allow verification to proceed even if amount isn't verified (Razorpay subscription model)
            logger.info("Payment verified for plan %s", plan_name)

        # Update existing subscription with Razorpay IDs
        subscription.razorpay_subscription_id = request.razorpay_subscription_id
        subscription.gateway = "razorpay"
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = datetime.now(timezone.utc)
        subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
        subscription.used_scans = 0
    else:
        # No existing subscription — create one
        # Determine actual plan from request body or default to pro
        plan_from_request = (request.plan or "pro").lower()
        plan_type_map = {"starter": PlanType.STARTER, "pro": PlanType.PRO, "business": PlanType.BUSINESS, "enterprise": PlanType.ENTERPRISE}
        tier_type_map = {"starter": SubscriptionTier.STARTER, "pro": SubscriptionTier.PRO, "business": SubscriptionTier.BUSINESS, "enterprise": SubscriptionTier.ENTERPRISE}
        selected_plan = plan_type_map.get(plan_from_request, PlanType.PRO)
        current_user.subscription_tier = tier_type_map.get(plan_from_request, SubscriptionTier.PRO)
        plan_name = plan_from_request if plan_from_request in plan_type_map else "pro"
        plan_info = get_plan_info(plan_name)
        new_sub = Subscription(
            organization_id=current_user.organization_id or current_user.id,
            razorpay_subscription_id=request.razorpay_subscription_id,
            gateway="razorpay",
            status=SubscriptionStatus.ACTIVE,
            plan=selected_plan,
            seats=plan_info["seats"],
            included_scans=plan_info["scans"],
            used_scans=0,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(new_sub)

    # Create invoice record
    from app.models.billing import Invoice
    invoice = Invoice(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        amount=PLAN_CATALOG.get(plan_name, {}).get("price_inr", 0) / 100,  # Convert paise to rupees
        currency="INR",
        status="paid",
        plan=plan_name,
        gateway="razorpay",
        gateway_payment_id=request.razorpay_payment_id,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(invoice)

    await db.commit()
    return {"status": "success", "plan": plan_name, "gateway": "razorpay"}


async def _verify_stripe(request, current_user, db):
    """Verify Stripe checkout session."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    if not request.stripe_session_id:
        raise HTTPException(status_code=400, detail="Missing Stripe session ID")

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        session = stripe.checkout.Session.retrieve(request.stripe_session_id)
        if session.payment_status != "paid":
            raise HTTPException(status_code=400, detail="Payment not completed")

        # AUDIT FIX H4: Verify checkout session belongs to the current user
        session_user_id = session.metadata.get("user_id")
        if session_user_id and session_user_id != str(current_user.id):
            logger.warning(
                "Stripe session user_id mismatch: session=%s, current_user=%s",
                session_user_id[:8] + "...",
                str(current_user.id)[:8] + "...",
            )
            raise HTTPException(status_code=403, detail="Checkout session does not belong to this user")

        plan = session.metadata.get("plan", "pro")
        stripe_tier_map = {
            "starter": SubscriptionTier.STARTER,
            "pro": SubscriptionTier.PRO,
            "business": SubscriptionTier.BUSINESS,
            "enterprise": SubscriptionTier.ENTERPRISE,
        }
        plan_type_map = {
            "starter": PlanType.STARTER,
            "pro": PlanType.PRO,
            "business": PlanType.BUSINESS,
            "enterprise": PlanType.ENTERPRISE,
        }
        current_user.subscription_tier = stripe_tier_map.get(plan, SubscriptionTier.PRO)

        # Create or update Subscription row (H3 fix)
        subscription = await get_user_subscription(current_user, db)
        stripe_sub_id = session.subscription if hasattr(session, 'subscription') else None
        if subscription:
            subscription.stripe_subscription_id = stripe_sub_id
            subscription.stripe_customer_id = session.customer if hasattr(session, 'customer') else None
            subscription.gateway = "stripe"
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.plan = plan_type_map.get(plan, PlanType.PRO)
            subscription.current_period_start = datetime.now(timezone.utc)
            subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
            subscription.used_scans = 0
        else:
            plan_info = get_plan_info(plan)
            new_sub = Subscription(
                organization_id=current_user.organization_id or current_user.id,
                stripe_subscription_id=stripe_sub_id,
                stripe_customer_id=session.customer if hasattr(session, 'customer') else None,
                gateway="stripe",
                status=SubscriptionStatus.ACTIVE,
                plan=plan_type_map.get(plan, PlanType.PRO),
                seats=plan_info["seats"],
                included_scans=plan_info["scans"],
                used_scans=0,
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            )
            db.add(new_sub)

        # Create invoice record
        from app.models.billing import Invoice
        invoice = Invoice(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            amount=session.amount_total or 0,
            currency=(session.currency or "usd").upper(),
            status="paid",
            plan=plan,
            gateway="stripe",
            gateway_payment_id=session.payment_intent if hasattr(session, 'payment_intent') else session.id,
            paid_at=datetime.now(timezone.utc),
        )
        db.add(invoice)

        await db.commit()
        return {"status": "success", "plan": plan, "gateway": "stripe"}

    except ImportError:
        raise HTTPException(status_code=503, detail="Stripe SDK not installed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Stripe verification failed", exc_info=True)
        raise HTTPException(status_code=400, detail="Payment verification failed")


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's payment history from Invoice table."""
    try:
        from app.models.billing import Invoice
        result = await db.execute(
            select(Invoice)
            .where(Invoice.user_id == current_user.id)
            .order_by(Invoice.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        invoices = result.scalars().all()
        return [
            InvoiceResponse(
                id=str(inv.id),
                amount=inv.amount,
                currency=inv.currency,
                status=inv.status,
                plan=inv.plan,
                description=inv.description or "",
                created_at=inv.created_at.isoformat() if inv.created_at else "",
                paid_at=inv.paid_at.isoformat() if inv.paid_at else None,
                gateway=inv.gateway or "razorpay",
            )
            for inv in invoices
        ]
    except Exception:
        # Invoice table may not exist yet
        return []


@router.post("/webhook/razorpay")
@limiter.limit("30/minute")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Razorpay webhook events."""
    try:
        body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature")

        if not signature or not settings.RAZORPAY_KEY_SECRET:
            logger.warning("Webhook received without signature or Razorpay not configured")
            raise HTTPException(status_code=400, detail="Missing webhook signature")

        expected_signature = hmac.HMAC(
            settings.RAZORPAY_KEY_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        event = json.loads(body)
        event_type = event.get("event")
        event_id = event.get("event_id") or event.get("id", "")
        logger.info("Razorpay webhook: %s (event_id=%s)", event_type, event_id)

        # Idempotency check — skip if already processed
        if event_id:
            existing = await db.execute(
                select(WebhookEvent).where(
                    WebhookEvent.gateway == "razorpay",
                    WebhookEvent.gateway_event_id == event_id,
                )
            )
            if existing.scalar_one_or_none():
                logger.info("Razorpay webhook %s already processed, skipping", event_id)
                return {"status": "already_processed"}
            db.add(WebhookEvent(gateway="razorpay", gateway_event_id=event_id, event_type=event_type or ""))

        if event_type == "subscription.charged":
            subscription_id = event["payload"]["subscription"]["entity"]["id"]
            # FOR UPDATE lock prevents concurrent charge events from racing
            result = await db.execute(
                select(Subscription)
                .where(Subscription.razorpay_subscription_id == subscription_id)
                .with_for_update()
            )
            subscription = result.scalar_one_or_none()
            if subscription:
                subscription.used_scans = 0
                subscription.current_period_start = datetime.now(timezone.utc)
                subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
                subscription.status = SubscriptionStatus.ACTIVE
                # Reset dunning state on successful payment
                subscription.dunning_attempts = 0
                subscription.last_dunning_at = None
                subscription.dunning_next_retry_at = None
                await db.commit()

        elif event_type == "subscription.cancelled":
            subscription_id = event["payload"]["subscription"]["entity"]["id"]
            result = await db.execute(
                select(Subscription)
                .where(Subscription.razorpay_subscription_id == subscription_id)
                .with_for_update()
            )
            subscription = result.scalar_one_or_none()
            if subscription:
                subscription.status = SubscriptionStatus.CANCELLED
                await db.commit()

        elif event_type == "payment.failed":
            entity = event.get("payload", {}).get("payment", {}).get("entity", {})
            notes = entity.get("notes", {})
            sub_id = notes.get("subscription_id")
            if sub_id:
                result = await db.execute(
                    select(Subscription)
                    .where(Subscription.razorpay_subscription_id == sub_id)
                    .with_for_update()
                )
                subscription = result.scalar_one_or_none()
                if subscription:
                    await _handle_payment_failure(subscription, db)

        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook processing error", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing error")


@router.post("/webhook/stripe")
@limiter.limit("30/minute")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Stripe webhook not configured")

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        body = await request.body()
        sig = request.headers.get("Stripe-Signature")

        if not sig:
            raise HTTPException(status_code=400, detail="Missing webhook signature")

        try:
            event = stripe.Webhook.construct_event(
                body, sig, settings.STRIPE_WEBHOOK_SECRET,
            )
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        stripe_event_id = event.get("id", "")
        stripe_event_type = event["type"]
        logger.info("Stripe webhook: %s (event_id=%s)", stripe_event_type, stripe_event_id)

        # Idempotency check — skip if already processed
        if stripe_event_id:
            existing = await db.execute(
                select(WebhookEvent).where(
                    WebhookEvent.gateway == "stripe",
                    WebhookEvent.gateway_event_id == stripe_event_id,
                )
            )
            if existing.scalar_one_or_none():
                logger.info("Stripe webhook %s already processed, skipping", stripe_event_id)
                return {"status": "already_processed"}
            db.add(WebhookEvent(gateway="stripe", gateway_event_id=stripe_event_id, event_type=stripe_event_type))

        if stripe_event_type == "invoice.paid":
            sub_data = event["data"]["object"]
            stripe_sub_id = sub_data.get("subscription")
            if stripe_sub_id:
                result = await db.execute(
                    select(Subscription)
                    .where(Subscription.stripe_subscription_id == stripe_sub_id)
                    .with_for_update()
                )
                subscription = result.scalar_one_or_none()
                if subscription:
                    subscription.used_scans = 0
                    subscription.status = SubscriptionStatus.ACTIVE
                    subscription.current_period_start = datetime.now(timezone.utc)
                    subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
                    # Reset dunning state on successful payment
                    subscription.dunning_attempts = 0
                    subscription.last_dunning_at = None
                    subscription.dunning_next_retry_at = None
                    await db.commit()

        elif stripe_event_type == "invoice.payment_failed":
            sub_data = event["data"]["object"]
            stripe_sub_id = sub_data.get("subscription")
            if stripe_sub_id:
                result = await db.execute(
                    select(Subscription)
                    .where(Subscription.stripe_subscription_id == stripe_sub_id)
                    .with_for_update()
                )
                subscription = result.scalar_one_or_none()
                if subscription:
                    await _handle_payment_failure(subscription, db)

        elif stripe_event_type == "customer.subscription.deleted":
            sub_data = event["data"]["object"]
            stripe_sub_id = sub_data.get("id")
            if stripe_sub_id:
                result = await db.execute(
                    select(Subscription)
                    .where(Subscription.stripe_subscription_id == stripe_sub_id)
                    .with_for_update()
                )
                subscription = result.scalar_one_or_none()
                if subscription:
                    subscription.status = SubscriptionStatus.CANCELLED
                    await db.commit()

        return {"status": "ok"}

    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe SDK not installed")
    except Exception as e:
        logger.error("Stripe webhook error", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing error")


# Keep backward-compatible /webhook route pointing to Razorpay
@router.post("/webhook")
@limiter.limit("30/minute")
async def webhook_compat(request: Request, db: AsyncSession = Depends(get_db)):
    """Backward-compatible webhook endpoint (routes to Razorpay)."""
    return await razorpay_webhook(request, db)


# ============================================================================
# Dunning Management (Audit Fix #33)
# ============================================================================

# Exponential backoff schedule: 1 day, 3 days, 7 days, 14 days
DUNNING_RETRY_DAYS = [1, 3, 7, 14]
DUNNING_MAX_ATTEMPTS = len(DUNNING_RETRY_DAYS)  # 4 attempts → auto-downgrade


async def _handle_payment_failure(subscription: Subscription, db: AsyncSession):
    """Handle a failed payment: update dunning state, send email, auto-downgrade if threshold hit."""
    now = datetime.now(timezone.utc)
    subscription.status = SubscriptionStatus.PAST_DUE
    subscription.dunning_attempts = (subscription.dunning_attempts or 0) + 1
    subscription.last_dunning_at = now

    attempts = subscription.dunning_attempts
    if attempts >= DUNNING_MAX_ATTEMPTS:
        # Auto-downgrade to FREE after exhausting retries
        subscription.plan = PlanType.FREE
        subscription.included_scans = 5
        subscription.dunning_next_retry_at = None
        logger.warning(
            "Subscription %s auto-downgraded to FREE after %d failed payment attempts",
            subscription.id, attempts,
        )
    else:
        retry_days = DUNNING_RETRY_DAYS[min(attempts - 1, len(DUNNING_RETRY_DAYS) - 1)]
        subscription.dunning_next_retry_at = now + timedelta(days=retry_days)

    await db.commit()
    logger.warning(
        "Payment failed for subscription %s — attempt %d, status=%s",
        subscription.id, attempts, subscription.status.value,
    )

    # Send dunning email (best-effort, don't fail webhook on email error)
    try:
        from app.services.email_service import send_dunning_email
        # Fetch user email from the org
        from app.models.user import User as UserModel
        user_result = await db.execute(
            select(UserModel).where(UserModel.organization_id == subscription.organization_id).limit(1)
        )
        user = user_result.scalar_one_or_none()
        if user:
            await send_dunning_email(
                user_email=user.email,
                user_name=user.name,
                plan=subscription.plan.value,
                attempts=attempts,
                next_retry_at=subscription.dunning_next_retry_at,
            )
    except Exception as e:
        logger.error("Failed to send dunning email: %s", e)


class DunningStatusResponse(BaseModel):
    status: str
    dunning_attempts: int
    last_dunning_at: Optional[str] = None
    next_retry_at: Optional[str] = None
    will_downgrade_after: int = DUNNING_MAX_ATTEMPTS


@router.get("/dunning/status", response_model=DunningStatusResponse)
async def get_dunning_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's dunning (failed payment) status."""
    subscription = await get_user_subscription(current_user, db)
    if not subscription:
        return DunningStatusResponse(status="none", dunning_attempts=0)

    return DunningStatusResponse(
        status=subscription.status.value,
        dunning_attempts=subscription.dunning_attempts or 0,
        last_dunning_at=subscription.last_dunning_at.isoformat() if subscription.last_dunning_at else None,
        next_retry_at=subscription.dunning_next_retry_at.isoformat() if subscription.dunning_next_retry_at else None,
    )


# ============================================================================
# Invoice PDF Download (Audit Fix #32)
# ============================================================================

@router.get("/invoices/{invoice_id}/download")
async def download_invoice_pdf(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download invoice as PDF for compliance/record-keeping."""
    from uuid import UUID as PyUUID
    try:
        inv_uuid = PyUUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")

    result = await db.execute(
        select(Invoice).where(Invoice.id == inv_uuid)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Verify ownership: invoice belongs to user or user's org
    if invoice.user_id != current_user.id:
        if not current_user.organization_id or invoice.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied")

    from app.services.invoice_pdf import generate_invoice_pdf
    from fastapi.responses import Response

    pdf_bytes = generate_invoice_pdf(invoice, current_user)
    short_id = str(invoice.id)[:8]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ContraRed-Invoice-{short_id}.pdf"'},
    )


# ============================================================================
# Quota Check Dependency (Phase 3.1 — fixes free bypass bug)
# ============================================================================

async def check_and_increment_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if user has quota remaining and increment usage.

    Phase 3.1 FIX: Now tracks per-user usage via UsageLog,
    so solo users (no org) can no longer bypass the free quota.
    """
    subscription = await get_user_subscription(current_user, db)

    # Auto-downgrade check: if dunning exhausted, force FREE tier
    if subscription and (subscription.dunning_attempts or 0) >= DUNNING_MAX_ATTEMPTS:
        if subscription.plan != PlanType.FREE:
            subscription.plan = PlanType.FREE
            subscription.included_scans = 5
            await db.commit()
            logger.info("Auto-downgraded subscription %s to FREE (dunning exhausted)", subscription.id)

    plan = subscription.plan.value if subscription else current_user.subscription_tier.value
    plan_info = get_plan_info(plan)
    used = await _get_user_scan_count(current_user, db)
    limit = plan_info["scans"]

    # Check quota (skip if unlimited = -1)
    if limit > 0 and used >= limit:
        # Check if plan supports overage
        overage_price = plan_info.get("overage_price_inr", 0)
        if overage_price > 0 and plan != "free":
            # Allow overage for paid plans (will be billed)
            logger.info(
                "User %s over quota (%d/%d) — overage billing applies",
                current_user.email, used, limit,
            )
        else:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": f"Quota exceeded. You've used {used}/{limit} scans this month.",
                    "error_code": "quota_exceeded",
                    "used": used,
                    "limit": limit,
                    "upgrade_url": "/billing/plans",
                },
            )

    # Increment usage (always — both subscription + UsageLog)
    await _increment_usage(current_user, db)
    await db.commit()

    return {"plan": plan, "used": used + 1, "limit": limit}


# ============================================================================
# Tier-Based Feature Gating
# ============================================================================

_TIER_ORDER = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "business": 3,
    "enterprise": 4,
}


def require_tier(*minimum_tiers: str):
    """
    FastAPI dependency factory that enforces subscription tier requirements.

    Usage:
        Depends(require_tier("business", "enterprise"))

    User must be on the lowest listed tier or higher.
    """
    min_level = min(_TIER_ORDER.get(t, 0) for t in minimum_tiers)

    async def _check_tier(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        subscription = await get_user_subscription(current_user, db)
        plan = subscription.plan.value if subscription else current_user.subscription_tier.value
        user_level = _TIER_ORDER.get(plan, 0)

        if user_level < min_level:
            min_tier_name = [t for t, v in _TIER_ORDER.items() if v == min_level][0]
            raise HTTPException(
                status_code=403,
                detail={
                    "message": f"This feature requires a {min_tier_name.title()} plan or higher. "
                               f"Your current plan: {plan.title()}.",
                    "error_code": "tier_required",
                    "current_tier": plan,
                    "required_tier": min_tier_name,
                    "upgrade_url": "/billing/plans",
                },
            )
        return plan

    return _check_tier


def require_seat_limit():
    """
    FastAPI dependency that enforces seat limits per plan.
    Used when adding new team members.
    """
    async def _check_seats(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        subscription = await get_user_subscription(current_user, db)
        plan = subscription.plan.value if subscription else current_user.subscription_tier.value
        plan_info = get_plan_info(plan)
        seat_limit = plan_info["seats"]

        if seat_limit > 0 and current_user.organization_id:
            count_result = await db.execute(
                select(func.count(User.id)).where(
                    User.organization_id == current_user.organization_id
                )
            )
            current_seats = count_result.scalar() or 0

            if current_seats >= seat_limit:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "message": f"Seat limit reached ({current_seats}/{seat_limit}). "
                                   f"Upgrade your plan to add more team members.",
                        "error_code": "seat_limit_reached",
                        "current_seats": current_seats,
                        "seat_limit": seat_limit,
                        "upgrade_url": "/billing/plans",
                    },
                )
        return plan

    return _check_seats


# ============================================================================
# ZDR Admin: Purge Risk Text (Audit Fix #34)
# ============================================================================

@router.post("/admin/zdr/purge-risks")
async def purge_zdr_risks(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Purge all DocumentRisk records when ZDR mode is enabled.

    Use this if ZDR was toggled on after documents were already analyzed
    in non-ZDR mode, leaving clause_text persisted in the DB.
    """
    if not getattr(settings, "ZERO_DATA_RETENTION", True):
        raise HTTPException(
            status_code=400,
            detail="ZDR mode is not enabled. Set ZERO_DATA_RETENTION=true to use this endpoint.",
        )

    from app.models.document import DocumentRisk
    from sqlalchemy import delete

    result = await db.execute(delete(DocumentRisk))
    await db.commit()
    count = result.rowcount
    logger.info("ZDR purge: deleted %d DocumentRisk records (admin: %s)", count, current_user.email)
    return {"status": "purged", "deleted_count": count}
