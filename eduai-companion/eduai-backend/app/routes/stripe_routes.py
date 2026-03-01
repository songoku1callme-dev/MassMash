"""Stripe integration routes for Free/Pro/Max subscriptions.

Handles:
- Creating Checkout sessions for Pro (4.99 EUR/month) and Max (19.99 EUR/month)
- Webhook handling with dual secrets for redundancy/failover
- Subscription status checking with tier info

STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET_1, STRIPE_WEBHOOK_SECRET_2 must be set.
STRIPE_PUBLISHABLE_KEY is safe to expose to the frontend.
"""
import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stripe", tags=["stripe"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_WEBHOOK_SECRET_1 = os.getenv("STRIPE_WEBHOOK_SECRET_1", "")
STRIPE_WEBHOOK_SECRET_2 = os.getenv("STRIPE_WEBHOOK_SECRET_2", "")
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY)

# Price tiers in cents
PRO_PRICE_CENTS = 499
PRO_PRICE_EUR = "4.99"
MAX_PRICE_CENTS = 1999
MAX_PRICE_EUR = "19.99"

# Free tier limits
FREE_OCR_LIMIT = 50  # per month
FREE_SPEECH_LIMIT = 50  # per month


class CheckoutRequest(BaseModel):
    success_url: str = ""
    cancel_url: str = ""
    plan: str = "pro"  # "pro" or "max"


class SubscriptionStatusResponse(BaseModel):
    is_pro: bool
    subscription_tier: str = "free"
    stripe_customer_id: str = ""
    pro_since: str = ""
    stripe_enabled: bool = False


@router.get("/config")
async def stripe_config():
    """Return Stripe configuration for the frontend (safe to expose)."""
    return {
        "enabled": STRIPE_ENABLED,
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "pro_price_eur": PRO_PRICE_EUR,
        "max_price_eur": MAX_PRICE_EUR,
        "plans": {
            "pro": {"price_eur": PRO_PRICE_EUR, "price_cents": PRO_PRICE_CENTS},
            "max": {"price_eur": MAX_PRICE_EUR, "price_cents": MAX_PRICE_CENTS},
        },
    }


@router.post("/create-checkout")
async def create_checkout(
    req: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a Stripe Checkout session for Pro or Max subscription."""
    if not STRIPE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Stripe ist nicht konfiguriert. Bitte STRIPE_SECRET_KEY setzen.",
        )

    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    user_id = current_user["id"]
    user_email = current_user["email"]

    # Determine plan details
    if req.plan == "max":
        price_cents = MAX_PRICE_CENTS
        plan_name = "EduAI Max"
        plan_desc = "GPT-4o Priority, 20 KI-Stile, 300+ Quiz-Themen, Wochen-Coach, Abitur-Sim, Internet-Recherche"
        target_tier = "max"
    else:
        price_cents = PRO_PRICE_CENTS
        plan_name = "EduAI Pro"
        plan_desc = "Unbegrenzt KI-Tutor, OCR, Spracheingabe, 8 KI-Stile, 25 Quiz-Themen"
        target_tier = "pro"

    # Check current subscription
    cursor = await db.execute(
        "SELECT stripe_customer_id, subscription_tier FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    row_dict = dict(row) if row else {}
    stripe_customer_id = row_dict.get("stripe_customer_id", "")
    current_tier = row_dict.get("subscription_tier", "free")

    # Prevent duplicate subscription at same tier
    if current_tier == target_tier:
        raise HTTPException(
            status_code=400,
            detail=f"Du hast bereits ein {target_tier.capitalize()}-Abo!",
        )

    # Create or reuse Stripe customer
    if not stripe_customer_id:
        customer = stripe.Customer.create(
            email=user_email,
            metadata={"eduai_user_id": str(user_id)},
        )
        stripe_customer_id = customer.id
        await db.execute(
            "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
            (stripe_customer_id, user_id),
        )
        await db.commit()

    # Determine URLs
    base_url = req.success_url.rsplit("/", 1)[0] if req.success_url else "http://localhost:5173"
    success_url = req.success_url or f"{base_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = req.cancel_url or f"{base_url}/pricing"

    # Create Checkout Session
    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        mode="subscription",
        line_items=[
            {
                "price_data": {
                    "currency": "eur",
                    "unit_amount": price_cents,
                    "recurring": {"interval": "month"},
                    "product_data": {
                        "name": plan_name,
                        "description": plan_desc,
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "eduai_user_id": str(user_id),
            "plan": target_tier,
        },
    )

    return {"checkout_url": session.url, "session_id": session.id}


def _verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
    """Try verifying webhook with both secrets for redundancy.

    Returns the parsed event dict, or raises HTTPException on failure.
    """
    import stripe

    secrets_to_try = []
    if STRIPE_WEBHOOK_SECRET_1:
        secrets_to_try.append(STRIPE_WEBHOOK_SECRET_1)
    if STRIPE_WEBHOOK_SECRET_2:
        secrets_to_try.append(STRIPE_WEBHOOK_SECRET_2)
    if STRIPE_WEBHOOK_SECRET:
        secrets_to_try.append(STRIPE_WEBHOOK_SECRET)

    if not secrets_to_try:
        # No webhook secret configured - parse without verification (dev mode)
        logger.warning("Stripe webhook signature NOT verified (no webhook secrets configured)")
        return json.loads(payload)

    last_error = None
    for secret in secrets_to_try:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
            return event
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            last_error = e
            continue

    logger.error("Stripe webhook signature verification failed with all secrets: %s", last_error)
    raise HTTPException(status_code=400, detail="Invalid signature")


def _tier_from_amount(amount_cents: int) -> str:
    """Determine subscription tier from price amount."""
    if amount_cents >= 1499:  # Max tier (19.99 or legacy 14.99)
        return "max"
    elif amount_cents >= PRO_PRICE_CENTS:
        return "pro"
    return "free"


@router.post("/webhook")
async def stripe_webhook(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    """Handle Stripe webhook events for subscription lifecycle.

    Events handled:
    - checkout.session.completed -> activate subscription tier
    - customer.subscription.updated -> update tier on plan change
    - customer.subscription.deleted -> deactivate to free

    Uses dual webhook secrets for redundancy/failover.
    """
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = _verify_webhook_signature(payload, sig_header)

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("eduai_user_id")
        plan = data.get("metadata", {}).get("plan", "pro")
        customer_id = data.get("customer", "")

        if user_id:
            is_pro = 1 if plan in ("pro", "max") else 0
            await db.execute(
                """UPDATE users SET is_pro = ?, subscription_tier = ?,
                   stripe_customer_id = ?, pro_since = datetime('now')
                   WHERE id = ?""",
                (is_pro, plan, customer_id, int(user_id)),
            )
            await db.commit()
            logger.info(
                "Subscription activated: user=%s tier=%s customer=%s",
                user_id, plan, customer_id,
            )

    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer", "")
        items = data.get("items", {}).get("data", [])
        if items and customer_id:
            amount = items[0].get("price", {}).get("unit_amount", 0)
            new_tier = _tier_from_amount(amount)
            is_pro = 1 if new_tier in ("pro", "max") else 0
            await db.execute(
                "UPDATE users SET is_pro = ?, subscription_tier = ? WHERE stripe_customer_id = ?",
                (is_pro, new_tier, customer_id),
            )
            await db.commit()
            logger.info("Subscription updated: customer=%s tier=%s", customer_id, new_tier)

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer", "")
        if customer_id:
            await db.execute(
                "UPDATE users SET is_pro = 0, subscription_tier = 'free' WHERE stripe_customer_id = ?",
                (customer_id,),
            )
            await db.commit()
            logger.info("Subscription cancelled: customer=%s", customer_id)

    return {"status": "ok"}


@router.get("/subscription-status", response_model=SubscriptionStatusResponse)
async def subscription_status(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Check current user's subscription status (tier, pro status)."""
    cursor = await db.execute(
        "SELECT is_pro, subscription_tier, stripe_customer_id, pro_since FROM users WHERE id = ?",
        (current_user["id"],),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    row_dict = dict(row)
    return SubscriptionStatusResponse(
        is_pro=bool(row_dict.get("is_pro", 0)),
        subscription_tier=row_dict.get("subscription_tier", "free") or "free",
        stripe_customer_id=row_dict.get("stripe_customer_id", "") or "",
        pro_since=row_dict.get("pro_since", "") or "",
        stripe_enabled=STRIPE_ENABLED,
    )


# Keep backward-compatible endpoint
@router.get("/pro-status")
async def pro_status(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Legacy endpoint - redirects to subscription-status."""
    return await subscription_status(current_user, db)
