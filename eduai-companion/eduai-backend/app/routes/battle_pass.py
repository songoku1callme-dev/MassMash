"""Battle Pass Gamification routes.

Supreme 11.0 Phase 8: 50-level seasonal progression with rewards.
XP from quizzes, tournaments, daily learning, Feynman tests.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/battle-pass", tags=["battle-pass"])

# 50 levels with rewards
BATTLE_PASS_REWARDS = [
    {"level": 1, "xp_required": 0, "reward": "Willkommens-Badge", "type": "badge", "icon": "award"},
    {"level": 2, "xp_required": 200, "reward": "Dark Mode Theme", "type": "theme", "icon": "palette"},
    {"level": 3, "xp_required": 400, "reward": "+10% XP Boost (1h)", "type": "boost", "icon": "zap"},
    {"level": 4, "xp_required": 600, "reward": "Stern-Profilrahmen", "type": "frame", "icon": "star"},
    {"level": 5, "xp_required": 800, "reward": "Yoda KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 6, "xp_required": 1000, "reward": "Ocean Theme", "type": "theme", "icon": "palette"},
    {"level": 7, "xp_required": 1200, "reward": "Hint-Token x3", "type": "boost", "icon": "lightbulb"},
    {"level": 8, "xp_required": 1400, "reward": "Gold Profilrahmen", "type": "frame", "icon": "crown"},
    {"level": 9, "xp_required": 1600, "reward": "+25% XP Boost (1h)", "type": "boost", "icon": "zap"},
    {"level": 10, "xp_required": 1800, "reward": "Sherlock KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 11, "xp_required": 2100, "reward": "Sunset Theme", "type": "theme", "icon": "palette"},
    {"level": 12, "xp_required": 2400, "reward": "Skip-Token x3", "type": "boost", "icon": "skip-forward"},
    {"level": 13, "xp_required": 2700, "reward": "Diamant Profilrahmen", "type": "frame", "icon": "gem"},
    {"level": 14, "xp_required": 3000, "reward": "Pirat KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 15, "xp_required": 3300, "reward": "+50% XP Boost (1h)", "type": "boost", "icon": "zap"},
    {"level": 16, "xp_required": 3600, "reward": "Forest Theme", "type": "theme", "icon": "palette"},
    {"level": 17, "xp_required": 3900, "reward": "Emoji-Pack", "type": "cosmetic", "icon": "smile"},
    {"level": 18, "xp_required": 4200, "reward": "Professor KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 19, "xp_required": 4500, "reward": "Platin Profilrahmen", "type": "frame", "icon": "gem"},
    {"level": 20, "xp_required": 4800, "reward": "Doppel-XP (24h)", "type": "boost", "icon": "zap"},
    {"level": 21, "xp_required": 5200, "reward": "Neon Theme", "type": "theme", "icon": "palette"},
    {"level": 22, "xp_required": 5600, "reward": "Hint-Token x5", "type": "boost", "icon": "lightbulb"},
    {"level": 23, "xp_required": 6000, "reward": "Anime KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 24, "xp_required": 6400, "reward": "Regenbogen Profilrahmen", "type": "frame", "icon": "rainbow"},
    {"level": 25, "xp_required": 6800, "reward": "1 Woche Pro gratis", "type": "subscription", "icon": "crown"},
    {"level": 26, "xp_required": 7200, "reward": "Galaxy Theme", "type": "theme", "icon": "palette"},
    {"level": 27, "xp_required": 7600, "reward": "+75% XP Boost (1h)", "type": "boost", "icon": "zap"},
    {"level": 28, "xp_required": 8000, "reward": "Wissenschaftler KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 29, "xp_required": 8400, "reward": "Feuer Profilrahmen", "type": "frame", "icon": "flame"},
    {"level": 30, "xp_required": 8800, "reward": "Skip-Token x5", "type": "boost", "icon": "skip-forward"},
    {"level": 31, "xp_required": 9300, "reward": "Cyberpunk Theme", "type": "theme", "icon": "palette"},
    {"level": 32, "xp_required": 9800, "reward": "Doppel-XP (48h)", "type": "boost", "icon": "zap"},
    {"level": 33, "xp_required": 10300, "reward": "Rapper KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 34, "xp_required": 10800, "reward": "Kristall Profilrahmen", "type": "frame", "icon": "gem"},
    {"level": 35, "xp_required": 11300, "reward": "Retro Theme", "type": "theme", "icon": "palette"},
    {"level": 36, "xp_required": 11800, "reward": "Hint-Token x10", "type": "boost", "icon": "lightbulb"},
    {"level": 37, "xp_required": 12300, "reward": "Sportler KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 38, "xp_required": 12800, "reward": "Legendaer Profilrahmen", "type": "frame", "icon": "trophy"},
    {"level": 39, "xp_required": 13300, "reward": "+100% XP Boost (1h)", "type": "boost", "icon": "zap"},
    {"level": 40, "xp_required": 13800, "reward": "1 Monat Pro gratis", "type": "subscription", "icon": "crown"},
    {"level": 41, "xp_required": 14400, "reward": "Aurora Theme", "type": "theme", "icon": "palette"},
    {"level": 42, "xp_required": 15000, "reward": "Doppel-XP (7 Tage)", "type": "boost", "icon": "zap"},
    {"level": 43, "xp_required": 15600, "reward": "Einstein KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 44, "xp_required": 16200, "reward": "Drachen Profilrahmen", "type": "frame", "icon": "flame"},
    {"level": 45, "xp_required": 16800, "reward": "Matrix Theme", "type": "theme", "icon": "palette"},
    {"level": 46, "xp_required": 17400, "reward": "Skip-Token x10", "type": "boost", "icon": "skip-forward"},
    {"level": 47, "xp_required": 18000, "reward": "Genie KI-Persönlichkeit", "type": "ki_personality", "icon": "bot"},
    {"level": 48, "xp_required": 18600, "reward": "Mythisch Profilrahmen", "type": "frame", "icon": "trophy"},
    {"level": 49, "xp_required": 19200, "reward": "+200% XP Boost (24h)", "type": "boost", "icon": "zap"},
    {"level": 50, "xp_required": 20000, "reward": "1 Monat Max gratis + Exklusiver Titel", "type": "subscription", "icon": "crown"},
]


@router.get("/status")
async def get_battle_pass_status(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get current Battle Pass status and progress."""
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT * FROM battle_pass WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()

    if not row:
        # Initialize battle pass for user
        await db.execute(
            "INSERT OR IGNORE INTO battle_pass (user_id) VALUES (?)",
            (user_id,),
        )
        await db.commit()
        current_level = 1
        current_xp = 0
        claimed = []
    else:
        rd = dict(row)
        current_level = rd["current_level"]
        current_xp = rd["current_xp"]
        try:
            claimed = json.loads(rd["claimed_rewards"])
        except (json.JSONDecodeError, TypeError):
            claimed = []

    # Calculate progress to next level
    current_reward = next((r for r in BATTLE_PASS_REWARDS if r["level"] == current_level), BATTLE_PASS_REWARDS[0])
    next_reward = next((r for r in BATTLE_PASS_REWARDS if r["level"] == current_level + 1), None)
    xp_for_current = current_reward["xp_required"]
    xp_for_next = next_reward["xp_required"] if next_reward else current_reward["xp_required"] + 200
    progress_xp = current_xp - xp_for_current
    needed_xp = xp_for_next - xp_for_current

    return {
        "saison": "Fruehling 2026",
        "current_level": current_level,
        "max_level": 50,
        "current_xp": current_xp,
        "xp_for_next_level": xp_for_next,
        "progress_percent": round(min(progress_xp / needed_xp * 100, 100), 1) if needed_xp > 0 else 100,
        "current_reward": current_reward,
        "next_reward": next_reward,
        "claimed_rewards": claimed,
        "all_rewards": BATTLE_PASS_REWARDS,
    }


@router.post("/claim/{level}")
async def claim_reward(
    level: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Claim a Battle Pass reward."""
    user_id = current_user["id"]

    # Find reward
    reward = next((r for r in BATTLE_PASS_REWARDS if r["level"] == level), None)
    if not reward:
        raise HTTPException(status_code=404, detail="Level nicht gefunden")

    # Check if user has reached this level
    cursor = await db.execute(
        "SELECT current_level, current_xp, claimed_rewards FROM battle_pass WHERE user_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Battle Pass nicht initialisiert")

    rd = dict(row)
    if rd["current_xp"] < reward["xp_required"]:
        raise HTTPException(status_code=400, detail="Nicht genug XP für dieses Level")

    try:
        claimed = json.loads(rd["claimed_rewards"])
    except (json.JSONDecodeError, TypeError):
        claimed = []

    if level in claimed:
        raise HTTPException(status_code=400, detail="Belohnung bereits abgeholt")

    claimed.append(level)
    await db.execute(
        "UPDATE battle_pass SET claimed_rewards = ? WHERE user_id = ?",
        (json.dumps(claimed), user_id),
    )
    await db.commit()

    return {
        "message": f"Belohnung freigeschaltet: {reward['reward']}!",
        "reward": reward,
        "claimed_levels": claimed,
    }


@router.post("/add-xp")
async def add_battle_pass_xp(
    xp_amount: int,
    source: str = "quiz",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Add XP to Battle Pass (called internally after activities)."""
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT current_level, current_xp FROM battle_pass WHERE user_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if not row:
        await db.execute("INSERT OR IGNORE INTO battle_pass (user_id) VALUES (?)", (user_id,))
        await db.commit()
        current_xp = 0
        current_level = 1
    else:
        rd = dict(row)
        current_xp = rd["current_xp"]
        current_level = rd["current_level"]

    new_xp = current_xp + xp_amount

    # Calculate new level
    new_level = current_level
    for reward in BATTLE_PASS_REWARDS:
        if new_xp >= reward["xp_required"]:
            new_level = reward["level"]

    level_up = new_level > current_level

    await db.execute(
        "UPDATE battle_pass SET current_xp = ?, current_level = ?, updated_at = datetime('now') WHERE user_id = ?",
        (new_xp, new_level, user_id),
    )
    await db.commit()

    result = {
        "new_xp": new_xp,
        "new_level": new_level,
        "xp_added": xp_amount,
        "source": source,
        "level_up": level_up,
    }

    if level_up:
        new_reward = next((r for r in BATTLE_PASS_REWARDS if r["level"] == new_level), None)
        if new_reward:
            result["new_reward"] = new_reward

    return result
