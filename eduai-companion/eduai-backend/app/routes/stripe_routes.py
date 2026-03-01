"""Stripe integration routes for Pro subscriptions.

Handles:
- Creating Checkout sessions for Pro upgrades (4.99 EUR/month)
- Webhook handling for subscription lifecycle events
- Pro status checking

STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET must be set in environment.
STRIPE_PUBLISHABLE_KEY is safe to expose to the frontend.
"""
import os
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
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY)

# Pro plan price in cents (4.99 EUR)
PRO_PRICE_CENTS = 499
PRO_PRICE_EUR = "4.99"

# Free tier limits
FREE_OCR_LIMIT = 50  # per month
FREE_SPEECH_LIMIT = 50  # per month


class CheckoutRequest(BaseModel):
    success_url: str = ""
    cancel_url: str = ""


class ProStatusResponse(BaseModel):
    is_pro: bool
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
    }


@router.post("/create-checkout")
async def create_checkout(
    req: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a Stripe Checkout session for Pro subscription (4.99 EUR/month)."""
    if not STRIPE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Stripe ist nicht konfiguriert. Bitte STRIPE_SECRET_KEY setzen.",
        )

    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    user_id = current_user["id"]
    user_email = current_user["email"]

    # Check if user already has a Stripe customer ID
    cursor = await db.execute(
        "SELECT stripe_customer_id, is_pro FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    row_dict = dict(row) if row else {}
    stripe_customer_id = row_dict.get("stripe_customer_id", "")

    if row_dict.get("is_pro"):
        raise HTTPException(status_code=400, detail="Du hast bereits ein Pro-Abo!")

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
                    "unit_amount": PRO_PRICE_CENTS,
                    "recurring": {"interval": "month"},
                    "product_data": {
                        "name": "EduAI Pro",
                        "description": "Unbegrenzt KI-Tutor, OCR, Spracheingabe + Wochenberichte",
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"eduai_user_id": str(user_id)},
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    """Handle Stripe webhook events for subscription lifecycle.

    Events handled:
    - checkout.session.completed → activate Pro
    - customer.subscription.deleted → deactivate Pro
    """
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify webhook signature if secret is set
    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error("Stripe webhook signature verification failed: %s", e)
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        import json
        event = json.loads(payload)
        logger.warning("Stripe webhook signature NOT verified (no STRIPE_WEBHOOK_SECRET)")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("eduai_user_id")
        customer_id = data.get("customer", "")
        if user_id:
            await db.execute(
                "UPDATE users SET is_pro = 1, stripe_customer_id = ?, pro_since = datetime('now') WHERE id = ?",
                (customer_id, int(user_id)),
            )
            await db.commit()
            logger.info("Pro activated for user %s (customer %s)", user_id, customer_id)

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer", "")
        if customer_id:
            await db.execute(
                "UPDATE users SET is_pro = 0 WHERE stripe_customer_id = ?",
                (customer_id,),
            )
            await db.commit()
            logger.info("Pro deactivated for customer %s", customer_id)

    return {"status": "ok"}


@router.get("/pro-status", response_model=ProStatusResponse)
async def pro_status(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Check current user's Pro subscription status."""
    cursor = await db.execute(
        "SELECT is_pro, stripe_customer_id, pro_since FROM users WHERE id = ?",
        (current_user["id"],),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    row_dict = dict(row)
    return ProStatusResponse(
        is_pro=bool(row_dict.get("is_pro", 0)),
        stripe_customer_id=row_dict.get("stripe_customer_id", "") or "",
        pro_since=row_dict.get("pro_since", "") or "",
        stripe_enabled=STRIPE_ENABLED,
    )
