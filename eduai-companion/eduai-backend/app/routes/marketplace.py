"""Lehrer-Marketplace routes.

Supreme 11.0: Teachers sell quiz sets and flashcard decks. Payment required for paid items.
"""
import json
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


@router.get("/items")
async def list_marketplace_items(
    category: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all marketplace items."""
    if category:
        cursor = await db.execute(
            """SELECT mi.*, u.username as creator_name FROM marketplace_items mi
            JOIN users u ON u.id = mi.creator_id
            WHERE mi.is_active = 1 AND mi.item_type = ?
            ORDER BY mi.downloads DESC LIMIT 50""",
            (category,),
        )
    else:
        cursor = await db.execute(
            """SELECT mi.*, u.username as creator_name FROM marketplace_items mi
            JOIN users u ON u.id = mi.creator_id
            WHERE mi.is_active = 1
            ORDER BY mi.downloads DESC LIMIT 50""",
        )
    rows = await cursor.fetchall()

    items = []
    for row in rows:
        rd = dict(row)
        items.append({
            "id": rd["id"],
            "title": rd["title"],
            "description": rd["description"],
            "price_cents": rd["price_cents"],
            "price_display": f"{rd['price_cents'] / 100:.2f}",
            "item_type": rd["item_type"],
            "downloads": rd["downloads"],
            "rating": rd["rating"],
            "creator_name": rd["creator_name"],
            "created_at": rd["created_at"],
        })

    return {"items": items}


@router.post("/create")
async def create_marketplace_item(
    title: str,
    description: str = "",
    price_cents: int = 499,
    item_type: str = "quiz_set",
    content_json: str = "[]",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new marketplace item (teacher)."""
    user_id = current_user["id"]

    if item_type not in ("quiz_set", "flashcard_deck", "lernplan"):
        raise HTTPException(status_code=400, detail="Ungueltiger Typ")

    if price_cents < 0 or price_cents > 9999:
        raise HTTPException(status_code=400, detail="Preis muss zwischen 0 und 99.99 Euro sein")

    cursor = await db.execute(
        """INSERT INTO marketplace_items (creator_id, title, description, price_cents, item_type, content_json)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, title, description, price_cents, item_type, content_json),
    )
    await db.commit()

    return {
        "id": cursor.lastrowid,
        "title": title,
        "price_cents": price_cents,
        "message": "Marketplace-Item erstellt!",
    }


@router.post("/buy/{item_id}")
async def buy_marketplace_item(
    item_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Purchase a paid marketplace item via Stripe."""
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT * FROM marketplace_items WHERE id = ? AND is_active = 1",
        (item_id,),
    )
    item = await cursor.fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden")

    item_dict = dict(item)

    if item_dict["price_cents"] == 0:
        raise HTTPException(status_code=400, detail="Dieses Item ist kostenlos, nutze /download")

    # Check if already purchased
    cursor = await db.execute(
        "SELECT id FROM marketplace_purchases WHERE user_id = ? AND item_id = ?",
        (user_id, item_id),
    )
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Bereits gekauft")

    # Create Stripe Payment Intent
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    client_secret = ""
    payment_intent_id = ""
    if stripe_key:
        try:
            import stripe
            stripe.api_key = stripe_key
            intent = stripe.PaymentIntent.create(
                amount=item_dict["price_cents"],
                currency="eur",
                metadata={"item_id": str(item_id), "user_id": str(user_id)},
            )
            client_secret = intent.client_secret
            payment_intent_id = intent.id
        except Exception as e:
            logger.error("Stripe PaymentIntent failed: %s", e)
            raise HTTPException(status_code=500, detail="Zahlung konnte nicht erstellt werden")
    else:
        # Dev mode: auto-complete purchase
        payment_intent_id = f"dev_{user_id}_{item_id}"

    # Record purchase
    await db.execute(
        "INSERT INTO marketplace_purchases (user_id, item_id, payment_intent_id, amount_cents) VALUES (?, ?, ?, ?)",
        (user_id, item_id, payment_intent_id, item_dict["price_cents"]),
    )
    await db.commit()

    return {
        "message": "Kauf erfolgreich!",
        "client_secret": client_secret,
        "payment_intent_id": payment_intent_id,
        "item": {"id": item_id, "title": item_dict["title"], "price_cents": item_dict["price_cents"]},
    }


@router.post("/download/{item_id}")
async def download_marketplace_item(
    item_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Download a marketplace item. Free items can be downloaded directly.
    Paid items require a purchase first."""
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT * FROM marketplace_items WHERE id = ? AND is_active = 1",
        (item_id,),
    )
    item = await cursor.fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden")

    item_dict = dict(item)

    # Payment check: if item costs money, verify purchase exists
    if item_dict["price_cents"] > 0:
        cursor = await db.execute(
            "SELECT id FROM marketplace_purchases WHERE user_id = ? AND item_id = ?",
            (user_id, item_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(
                status_code=402,
                detail=f"Dieses Item kostet {item_dict['price_cents'] / 100:.2f} EUR. Bitte zuerst kaufen.",
            )

    # Increment downloads
    await db.execute(
        "UPDATE marketplace_items SET downloads = downloads + 1 WHERE id = ?",
        (item_id,),
    )
    await db.commit()

    return {
        "title": item_dict["title"],
        "item_type": item_dict["item_type"],
        "content": json.loads(item_dict["content_json"]),
        "message": "Download erfolgreich!",
    }


@router.post("/rate/{item_id}")
async def rate_marketplace_item(
    item_id: int,
    rating: float,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Rate a marketplace item (1-5 stars)."""
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Bewertung muss zwischen 1 und 5 sein")

    cursor = await db.execute(
        "SELECT rating, downloads FROM marketplace_items WHERE id = ?",
        (item_id,),
    )
    item = await cursor.fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden")

    item_dict = dict(item)
    # Simple average (in production, track individual ratings)
    old_rating = item_dict["rating"] or 0
    downloads = item_dict["downloads"] or 1
    new_rating = round((old_rating * (downloads - 1) + rating) / downloads, 1)

    await db.execute(
        "UPDATE marketplace_items SET rating = ? WHERE id = ?",
        (new_rating, item_id),
    )
    await db.commit()

    return {"message": "Bewertung gespeichert!", "new_rating": new_rating}
