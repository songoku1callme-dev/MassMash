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

DEFAULT_ITEMS = [
    # THEMES (100-300 XP)
    {"name":"Dark Pro Theme","cost":100,
     "category":"themes","icon":"moon",
     "description":"Exklusives dunkles Design"},
    {"name":"Neon Theme","cost":200,
     "category":"themes","icon":"zap",
     "description":"Leuchtendes Neon-Design"},
    {"name":"Sakura Theme","cost":300,
     "category":"themes","icon":"flower",
     "description":"Japanisches Kirschblüten-Design"},
    
    # KI-PERSÖNLICHKEITEN (200-500 XP)
    {"name":"Einstein Modus","cost":500,
     "category":"personalities","icon":"brain",
     "description":"KI erklärt wie Einstein"},
    {"name":"Sokrates Modus","cost":400,
     "category":"personalities","icon":"landmark",
     "description":"Sokratische Methode"},
    {"name":"Friendly Coach","cost":200,
     "category":"personalities","icon":"smile",
     "description":"Motivierender Lerncoach"},

    # POWER-UPS (150-500 XP)
    {"name":"Streak Freeze","cost":150,
     "category":"powerups","icon":"snowflake",
     "description":"Schützt deinen Streak 1x"},
    {"name":"Doppel-XP (1h)","cost":300,
     "category":"powerups","icon":"zap",
     "description":"2x XP für 1 Stunde"},
    {"name":"XP-Boost (24h)","cost":500,
     "category":"powerups","icon":"rocket",
     "description":"1.5x XP für 24 Stunden"},
    {"name":"Hint-Token (5x)","cost":100,
     "category":"powerups","icon":"lightbulb",
     "description":"5 Hinweise für Quiz"},

    # RAHMEN & COSMETICS (200-400 XP)
    {"name":"Gold-Rahmen","cost":400,
     "category":"cosmetics","icon":"crown",
     "description":"Goldener Avatar-Rahmen"},
    {"name":"Diamond-Rahmen","cost":800,
     "category":"cosmetics","icon":"gem",
     "description":"Diamant Avatar-Rahmen"},
    {"name":"Flame-Effekt","cost":300,
     "category":"cosmetics","icon":"flame",
     "description":"Flammen um deinen Avatar"},

    # PREMIUM (500-1500 XP)
    {"name":"Pro-Testwoche","cost":1000,
     "category":"premium","icon":"star",
     "description":"7 Tage Pro kostenlos"},
    {"name":"Bonus-Quiz Pack","cost":200,
     "category":"premium","icon":"book",
     "description":"50 Extra-Quizfragen"},
]

async def seed_shop_items_if_empty(db: aiosqlite.Connection):
    """Seed default shop items into DB if the shop_items table is empty."""
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM shop_items")
        row = await cursor.fetchone()
        count = row[0] if row else 0
        if count == 0:
            for item in DEFAULT_ITEMS:
                await db.execute(
                    """INSERT INTO shop_items (name, cost, category, icon, description)
                    VALUES (?, ?, ?, ?, ?)""",
                    (item["name"], item["cost"], item["category"],
                     item["icon"], item["description"]),
                )
            await db.commit()
            logger.info(f"Shop seeded with {len(DEFAULT_ITEMS)} default items")
    except Exception as e:
        logger.warning(f"Shop seeding skipped: {e}")



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

    # Try to load items from DB first; fall back to DEFAULT_ITEMS
    cursor = await db.execute("SELECT id, name, cost, category, icon, description FROM shop_items")
    db_rows = await cursor.fetchall()
    if db_rows:
        shop_list = [dict(r) for r in db_rows]
    else:
        # DB empty — seed and use DEFAULT_ITEMS in-memory
        await seed_shop_items_if_empty(db)
        shop_list = [{"id": i, **item} for i, item in enumerate(DEFAULT_ITEMS, start=1)]

    items_with_status = []
    for item in shop_list:
        item_id = str(item.get("id", item.get("name", "")))
        cost = item.get("cost", item.get("price", 0))
        items_with_status.append({
            **item,
            "cost": cost,
            "unlocked": item_id in unlocked,
            "can_afford": user_xp >= cost,
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

    # Find item from DB first, then fall back to DEFAULT_ITEMS
    cursor = await db.execute(
        "SELECT id, name, cost, category, icon, description FROM shop_items WHERE id = ?",
        (item_id,),
    )
    row = await cursor.fetchone()
    if row:
        item = dict(row)
    else:
        # Try matching by name in DEFAULT_ITEMS (for backwards compat)
        item = next(
            ({"id": item_id, **i} for i in DEFAULT_ITEMS if i["name"] == item_id),
            None,
        )
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden")

    item_cost = item.get("cost", 0)

    # Check if already owned (non-boost items)
    if item.get("category") != "powerups":
        cursor = await db.execute(
            "SELECT metadata FROM activity_log WHERE user_id = ? AND activity_type = 'shop_purchase'",
            (user_id,),
        )
        rows = await cursor.fetchall()
        for r in rows:
            try:
                data = json.loads(dict(r)["metadata"])
                if str(data.get("item_id")) == str(item_id):
                    raise HTTPException(status_code=400, detail="Item bereits freigeschaltet")
            except (json.JSONDecodeError, KeyError):
                pass

    # Check XP
    cursor = await db.execute(
        "SELECT xp FROM gamification WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    user_xp = dict(row)["xp"] if row else 0

    if user_xp < item_cost:
        raise HTTPException(status_code=400, detail=f"Nicht genug XP! Du brauchst {item_cost}, hast aber nur {user_xp}")

    # Deduct XP
    await db.execute(
        "UPDATE gamification SET xp = xp - ? WHERE user_id = ?",
        (item_cost, user_id),
    )

    # Log purchase
    await db.execute(
        """INSERT INTO activity_log (user_id, activity_type, subject, description, metadata)
        VALUES (?, 'shop_purchase', 'shop', ?, ?)""",
        (user_id, f"Gekauft: {item['name']} für {item_cost} XP",
         json.dumps({"item_id": str(item_id), "cost": item_cost})),
    )
    await db.commit()

    new_xp = user_xp - item_cost
    return {"message": f"{item['name']} freigeschaltet!", "item": item, "remaining_xp": new_xp}
