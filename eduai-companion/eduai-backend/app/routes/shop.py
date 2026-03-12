"""Belohnungs-Shop routes - XP for Themes, KI-Persönlichkeiten, Items.

Supreme 9.0 Phase 10: Users spend XP for unlockable items.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/shop", tags=["shop"])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Default Shop Items — werden automatisch geladen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SHOP_ITEMS = [
    # Themes (500 XP)
    {"id": "theme_dark_blue", "name": "Dark Blue Theme", "category": "theme", "price": 500, "icon": "palette", "description": "Dunkles Blau für konzentriertes Lernen"},
    {"id": "theme_purple", "name": "Purple Theme", "category": "theme", "price": 500, "icon": "palette", "description": "Elegantes Lila für kreative Köpfe"},
    {"id": "theme_sunset", "name": "Sunset Theme", "category": "theme", "price": 500, "icon": "palette", "description": "Warme Sonnenuntergangsfarben"},
    {"id": "theme_forest", "name": "Forest Theme", "category": "theme", "price": 500, "icon": "palette", "description": "Natürliches Waldgrün"},
    {"id": "theme_ocean", "name": "Ocean Theme", "category": "theme", "price": 500, "icon": "palette", "description": "Tiefes Meeresblau"},
    {"id": "theme_cherry", "name": "Cherry Blossom Theme", "category": "theme", "price": 600, "icon": "palette", "description": "Zartes Kirschblüten-Rosa"},
    {"id": "theme_neon", "name": "Neon Cyber Theme", "category": "theme", "price": 750, "icon": "palette", "description": "Leuchtende Neonfarben im Cyber-Stil"},
    # KI-Persönlichkeiten (1000 XP)
    {"id": "ki_yoda", "name": "Yoda KI-Persönlichkeit", "category": "ki", "price": 1000, "icon": "bot", "description": "Weise Antworten im Yoda-Stil"},
    {"id": "ki_sherlock", "name": "Sherlock KI-Persönlichkeit", "category": "ki", "price": 1000, "icon": "bot", "description": "Analytisch und deduktiv"},
    {"id": "ki_pirat", "name": "Pirat KI-Persönlichkeit", "category": "ki", "price": 1000, "icon": "bot", "description": "Arrr! Lernen auf hoher See"},
    {"id": "ki_rapper", "name": "Rapper KI-Persönlichkeit", "category": "ki", "price": 1000, "icon": "bot", "description": "Erklärt alles im Rap-Stil"},
    {"id": "ki_astronaut", "name": "Astronaut KI-Persönlichkeit", "category": "ki", "price": 1200, "icon": "bot", "description": "Wissen aus dem Weltall"},
    # Profilrahmen (750-2000 XP)
    {"id": "frame_gold", "name": "Gold Profilrahmen", "category": "frame", "price": 750, "icon": "crown", "description": "Goldener Rahmen für dein Profil"},
    {"id": "frame_diamond", "name": "Diamant Profilrahmen", "category": "frame", "price": 1500, "icon": "gem", "description": "Funkelnder Diamant-Rahmen"},
    {"id": "frame_fire", "name": "Feuer Profilrahmen", "category": "frame", "price": 1000, "icon": "flame", "description": "Lodernder Flammenrahmen"},
    {"id": "frame_rainbow", "name": "Regenbogen Profilrahmen", "category": "frame", "price": 2000, "icon": "rainbow", "description": "Schillernder Regenbogenrahmen"},
    # Boosts (150-500 XP)
    {"id": "boost_double_xp", "name": "Doppel-XP (1 Stunde)", "category": "boost", "price": 200, "icon": "zap", "description": "1 Stunde doppelte XP"},
    {"id": "boost_hint", "name": "Hint-Token für IQ-Test", "category": "boost", "price": 300, "icon": "lightbulb", "description": "Ein Hinweis im IQ-Test"},
    {"id": "boost_skip", "name": "Frage-Überspringen Token", "category": "boost", "price": 150, "icon": "skip-forward", "description": "Überspringe eine schwierige Frage"},
    {"id": "boost_streak_shield", "name": "Streak-Schutzschild", "category": "boost", "price": 500, "icon": "shield", "description": "Schützt deinen Streak für einen Tag"},
    {"id": "boost_extra_life", "name": "Extra Leben (Quiz)", "category": "boost", "price": 250, "icon": "heart", "description": "Ein zusätzlicher Versuch im Quiz"},
    # Titel & Badges (800-3000 XP)
    {"id": "title_genius", "name": "Titel: Genie", "category": "title", "price": 2000, "icon": "brain", "description": "Zeige allen, dass du ein Genie bist"},
    {"id": "title_nerd", "name": "Titel: Nerd", "category": "title", "price": 800, "icon": "glasses", "description": "Trage den Nerd-Titel mit Stolz"},
    {"id": "title_champion", "name": "Titel: Champion", "category": "title", "price": 3000, "icon": "trophy", "description": "Der ultimative Lern-Champion"},
]


@router.get("/items")
async def get_shop_items(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get all shop items with user's unlock status."""
    user_id = current_user["id"]

    # Get user's XP
    cursor = await db.execute(
        "SELECT xp FROM gamification WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    user_xp = dict(row)["xp"] if row else 0

    # Get user's unlocked items
    cursor = await db.execute(
        "SELECT metadata FROM activity_log WHERE user_id = ? AND activity_type = 'shop_purchase'",
        (user_id,),
    )
    rows = await cursor.fetchall()
    unlocked = set()
    for r in rows:
        try:
            data = json.loads(dict(r)["metadata"])
            unlocked.add(data.get("item_id", ""))
        except Exception:
            pass

    items_with_status = []
    for item in SHOP_ITEMS:
        items_with_status.append({
            **item,
            "unlocked": item["id"] in unlocked,
            "can_afford": user_xp >= item["price"],
        })

    return {"items": items_with_status, "user_xp": user_xp}


@router.post("/buy")
async def buy_item(
    item_id: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Buy an item from the shop with XP."""
    user_id = current_user["id"]

    # Find item
    item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden")

    # Check if already owned (non-boost items)
    if item["category"] != "boost":
        cursor = await db.execute(
            "SELECT metadata FROM activity_log WHERE user_id = ? AND activity_type = 'shop_purchase'",
            (user_id,),
        )
        rows = await cursor.fetchall()
        for r in rows:
            try:
                data = json.loads(dict(r)["metadata"])
                if data.get("item_id") == item_id:
                    raise HTTPException(status_code=400, detail="Item bereits freigeschaltet")
            except (json.JSONDecodeError, KeyError):
                pass

    # Check XP
    cursor = await db.execute(
        "SELECT xp FROM gamification WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    user_xp = dict(row)["xp"] if row else 0

    if user_xp < item["price"]:
        raise HTTPException(status_code=400, detail=f"Nicht genug XP! Du brauchst {item['price']}, hast aber nur {user_xp}")

    # Deduct XP
    await db.execute(
        "UPDATE gamification SET xp = xp - ? WHERE user_id = ?",
        (item["price"], user_id),
    )

    # Log purchase
    await db.execute(
        """INSERT INTO activity_log (user_id, activity_type, subject, description, metadata)
        VALUES (?, 'shop_purchase', 'shop', ?, ?)""",
        (user_id, f"Gekauft: {item['name']} für {item['price']} XP",
         json.dumps({"item_id": item_id, "price": item["price"]})),
    )
    await db.commit()

    new_xp = user_xp - item["price"]
    return {"message": f"{item['name']} freigeschaltet!", "item": item, "remaining_xp": new_xp}
