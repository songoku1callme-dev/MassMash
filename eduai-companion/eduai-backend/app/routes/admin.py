"""Admin routes: stats dashboard, grant subscriptions, coupon codes, user search.

Admin = user_id=1 OR username='admin' OR email contains 'admin' OR is_admin=1.
"""
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.monitoring import get_monitoring_frontend_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_EMAILS = ",".join(filter(None, [
    os.getenv("ADMIN_EMAIL", ""),
    os.getenv("ADMIN_EMAIL_2", ""),
    os.getenv("ADMIN_EMAIL_3", ""),
    os.getenv("ADMIN_EMAIL_4", ""),
]))


def is_admin_email(email: str) -> bool:
    """Check if email is in the admin list."""
    return email in [e.strip() for e in ADMIN_EMAILS.split(",") if e.strip()]


async def _is_admin(user: dict, db: aiosqlite.Connection) -> bool:
    """Check if user is an admin."""
    if user.get("id") == 1:
        return True
    if user.get("username", "") == "admin":
        return True
    # Dev token user (id=999) is always admin
    if user.get("id") == 999 and user.get("auth_provider") == "dev":
        return True
    # Max-tier users are admins
    if user.get("subscription_tier") == "max":
        return True
    user_email = user.get("email", "")
    if is_admin_email(user_email):
        return True
    if user_email == "admin@lumnos.de":
        return True
    try:
        cursor = await db.execute(
            "SELECT is_admin FROM users WHERE id = ?", (user["id"],)
        )
        row = await cursor.fetchone()
        if row and dict(row).get("is_admin", 0):
            return True
    except Exception:
        pass
    return False


def _require_admin(is_admin: bool) -> None:
    if not is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren haben Zugriff.")


class GrantSubscriptionRequest(BaseModel):
    user_id: int
    tier: str = "pro"
    duration_days: int = 30


class CreateCouponRequest(BaseModel):
    code: str
    tier: str = "pro"
    duration_days: int = 30
    max_uses: int = 100


@router.get("/is-admin")
async def check_is_admin(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Check if current user is admin."""
    admin = await _is_admin(current_user, db)
    return {"is_admin": admin}


@router.get("/token-usage")
async def get_token_usage_endpoint(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Return current Groq token usage stats (admin only).

    Shows daily token budget consumption for the Groq Free Tier (100K TPD).
    Helps admins monitor API usage and plan for scaling.
    """
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    from app.services.ai_engine import get_token_usage
    usage = get_token_usage()
    return usage


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Return platform statistics for the admin dashboard."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    stats: dict = {}

    cursor = await db.execute("SELECT COUNT(*) FROM users")
    row = await cursor.fetchone()
    stats["total_users"] = row[0] if row else 0

    cursor = await db.execute("SELECT COUNT(*) FROM users WHERE subscription_tier = 'pro'")
    row = await cursor.fetchone()
    stats["pro_users"] = row[0] if row else 0

    cursor = await db.execute("SELECT COUNT(*) FROM users WHERE subscription_tier = 'max'")
    row = await cursor.fetchone()
    stats["max_users"] = row[0] if row else 0

    cursor = await db.execute("SELECT COUNT(*) FROM chat_sessions")
    row = await cursor.fetchone()
    stats["total_chat_sessions"] = row[0] if row else 0

    cursor = await db.execute("SELECT COUNT(*) FROM quiz_results")
    row = await cursor.fetchone()
    stats["total_quizzes"] = row[0] if row else 0

    cursor = await db.execute("SELECT AVG(score) FROM quiz_results")
    row = await cursor.fetchone()
    stats["avg_quiz_score"] = round(row[0], 1) if row and row[0] is not None else 0.0

    cursor = await db.execute(
        """SELECT id, username, email, subscription_tier, pro_expires_at, billing_period
        FROM users WHERE subscription_tier != 'free'
        ORDER BY pro_since DESC LIMIT 50"""
    )
    rows = await cursor.fetchall()
    stats["active_subscriptions"] = [dict(r) for r in rows]

    try:
        cursor = await db.execute("SELECT COUNT(*) FROM coupons WHERE is_active = 1")
        row = await cursor.fetchone()
        stats["active_coupons"] = row[0] if row else 0
    except Exception:
        stats["active_coupons"] = 0

    try:
        cursor = await db.execute("SELECT COUNT(*) FROM tournaments")
        row = await cursor.fetchone()
        stats["total_tournaments"] = row[0] if row else 0
    except Exception:
        stats["total_tournaments"] = 0

    cursor = await db.execute(
        "SELECT COUNT(*) FROM activity_log WHERE created_at > datetime('now', '-1 day')"
    )
    row = await cursor.fetchone()
    stats["activity_last_24h"] = row[0] if row else 0

    cursor = await db.execute(
        "SELECT subject, COUNT(*) as cnt FROM chat_sessions GROUP BY subject ORDER BY cnt DESC"
    )
    rows = await cursor.fetchall()
    stats["subject_popularity"] = {row[0]: row[1] for row in rows}

    return stats


@router.get("/search-users")
async def search_users(
    query: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Search users by email or username."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    if not query:
        cursor = await db.execute(
            "SELECT id, username, email, subscription_tier, pro_expires_at, created_at FROM users ORDER BY id DESC LIMIT 50"
        )
    else:
        cursor = await db.execute(
            """SELECT id, username, email, subscription_tier, pro_expires_at, created_at
            FROM users WHERE username LIKE ? OR email LIKE ?
            ORDER BY id DESC LIMIT 50""",
            (f"%{query}%", f"%{query}%"),
        )
    rows = await cursor.fetchall()
    return {"users": [dict(r) for r in rows]}


@router.post("/grant-subscription")
async def grant_subscription(
    req: GrantSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Grant a subscription to a user (admin only)."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    if req.duration_days > 0:
        expires_at = (datetime.now() + timedelta(days=req.duration_days)).isoformat()
    else:
        expires_at = ""

    await db.execute(
        """UPDATE users SET subscription_tier = ?, is_pro = 1,
           pro_expires_at = ?, pro_since = datetime('now')
           WHERE id = ?""",
        (req.tier, expires_at, req.user_id),
    )
    await db.commit()

    await db.execute(
        "INSERT INTO admin_logs (admin_id, action, target_user_id, details) VALUES (?, ?, ?, ?)",
        (current_user["id"], "grant_subscription",
         req.user_id, f"tier={req.tier}, days={req.duration_days}"),
    )
    await db.commit()

    return {
        "message": f"Abo {req.tier} f\u00fcr User {req.user_id} aktiviert ({req.duration_days} Tage)",
        "user_id": req.user_id,
        "tier": req.tier,
        "expires_at": expires_at,
    }


@router.post("/create-coupon")
async def create_coupon(
    req: CreateCouponRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new coupon code (admin only)."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    code = req.code.strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Code darf nicht leer sein")

    cursor = await db.execute("SELECT id FROM coupons WHERE code = ?", (code,))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail=f"Code '{code}' existiert bereits")

    cursor = await db.execute(
        """INSERT INTO coupons (code, tier, duration_days, max_uses, created_by)
        VALUES (?, ?, ?, ?, ?)""",
        (code, req.tier, req.duration_days, req.max_uses, current_user["id"]),
    )
    await db.commit()

    return {
        "message": f"Gutschein '{code}' erstellt",
        "coupon_id": cursor.lastrowid,
        "code": code,
        "tier": req.tier,
        "duration_days": req.duration_days,
        "max_uses": req.max_uses,
    }


@router.get("/coupons")
async def list_coupons(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all coupon codes (admin only)."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    cursor = await db.execute("SELECT * FROM coupons ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return {"coupons": [dict(r) for r in rows]}


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(
    coupon_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Deactivate a coupon (admin only)."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    await db.execute("UPDATE coupons SET is_active = 0 WHERE id = ?", (coupon_id,))
    await db.commit()
    return {"message": "Gutschein deaktiviert"}


@router.post("/redeem-coupon")
async def redeem_coupon(
    code: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Redeem a coupon code (any user)."""
    user_id = current_user["id"]
    code = code.strip().upper()

    cursor = await db.execute(
        "SELECT * FROM coupons WHERE code = ? AND is_active = 1", (code,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ung\u00fcltiger oder abgelaufener Gutschein-Code")

    coupon = dict(row)

    if coupon["max_uses"] > 0 and coupon["current_uses"] >= coupon["max_uses"]:
        raise HTTPException(status_code=400, detail="Gutschein wurde bereits zu oft eingel\u00f6st")

    cursor = await db.execute(
        "SELECT id FROM coupon_redemptions WHERE coupon_id = ? AND user_id = ?",
        (coupon["id"], user_id),
    )
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Du hast diesen Gutschein bereits eingel\u00f6st")

    expires_at = (datetime.now() + timedelta(days=coupon["duration_days"])).isoformat()
    await db.execute(
        """UPDATE users SET subscription_tier = ?, is_pro = 1,
           pro_expires_at = ?, pro_since = datetime('now')
           WHERE id = ?""",
        (coupon["tier"], expires_at, user_id),
    )

    await db.execute(
        "INSERT INTO coupon_redemptions (coupon_id, user_id) VALUES (?, ?)",
        (coupon["id"], user_id),
    )
    await db.execute(
        "UPDATE coupons SET current_uses = current_uses + 1 WHERE id = ?",
        (coupon["id"],),
    )
    await db.commit()

    return {
        "message": f"Gutschein eingel\u00f6st! {coupon['tier'].capitalize()}-Abo f\u00fcr {coupon['duration_days']} Tage aktiviert.",
        "tier": coupon["tier"],
        "duration_days": coupon["duration_days"],
        "expires_at": expires_at,
    }


@router.get("/analytics")
async def get_analytics(
    days: int = 7,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Return analytics data for admin dashboard (daily signups, revenue, popular subjects)."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    # Daily new users for the last N days
    cursor = await db.execute(
        """SELECT date(created_at) as day, COUNT(*) as count
        FROM users WHERE created_at > datetime('now', ?)
        GROUP BY day ORDER BY day""",
        (f"-{days} days",),
    )
    rows = await cursor.fetchall()
    daily_signups = [{"day": r[0], "count": r[1]} for r in rows]

    # Revenue estimate (count of paid users)
    cursor = await db.execute(
        """SELECT subscription_tier, billing_period, COUNT(*) as cnt
        FROM users WHERE subscription_tier != 'free'
        GROUP BY subscription_tier, billing_period"""
    )
    rows = await cursor.fetchall()
    revenue_breakdown = []
    total_mrr = 0.0
    for r in rows:
        tier, period, cnt = r[0], r[1] or "monthly", r[2]
        if tier == "pro":
            price = 4.99 if period == "monthly" else 39.99 / 12
        elif tier == "max":
            price = 9.99 if period == "monthly" else 79.99 / 12
        else:
            price = 0
        mrr = price * cnt
        total_mrr += mrr
        revenue_breakdown.append({"tier": tier, "period": period, "users": cnt, "mrr": round(mrr, 2)})

    # Popular subjects (from chat sessions)
    cursor = await db.execute(
        """SELECT subject, COUNT(*) as cnt FROM chat_sessions
        GROUP BY subject ORDER BY cnt DESC LIMIT 10"""
    )
    rows = await cursor.fetchall()
    popular_subjects = [{"subject": r[0], "count": r[1]} for r in rows]

    # Tournament participants
    try:
        cursor = await db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM tournament_participants"
        )
        row = await cursor.fetchone()
        tournament_participants = row[0] if row else 0
    except Exception:
        tournament_participants = 0

    # IQ test stats
    try:
        cursor = await db.execute(
            "SELECT COUNT(*), AVG(iq_score) FROM iq_results"
        )
        row = await cursor.fetchone()
        iq_tests = {"total": row[0] if row else 0, "avg_iq": round(row[1], 1) if row and row[1] else 0}
    except Exception:
        iq_tests = {"total": 0, "avg_iq": 0}

    return {
        "daily_signups": daily_signups,
        "revenue": {"breakdown": revenue_breakdown, "total_mrr": round(total_mrr, 2)},
        "popular_subjects": popular_subjects,
        "tournament_participants": tournament_participants,
        "iq_tests": iq_tests,
    }


@router.post("/seed-themen")
async def seed_themen(
    fach: str = "Mathematik",
    bundesland: str = "Bayern",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Fächer-Expansion 5.0 Block 4: Lehrplan-konforme Quiz-Generierung.

    Uses Tavily API to search for real curriculum documents, then Groq to
    extract 50 concrete learning objectives. Admin only.
    """
    import json
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    groq_key = os.getenv("GROQ_API_KEY", "")

    if not tavily_key:
        raise HTTPException(status_code=400, detail="TAVILY_API_KEY nicht konfiguriert")

    # Step 1: Tavily search for real curriculum documents
    search_query = f"Bildungsstandards Lehrplan {fach} {bundesland} Gymnasium Sek II"
    tavily_results = []
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": search_query,
                    "search_depth": "advanced",
                    "max_results": 5,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for r in data.get("results", []):
                    tavily_results.append({
                        "title": r.get("title", ""),
                        "content": r.get("content", "")[:500],
                        "url": r.get("url", ""),
                    })
    except Exception as e:
        logger.error("Tavily search failed: %s", e)

    if not tavily_results:
        raise HTTPException(status_code=502, detail="Keine Lehrplan-Quellen gefunden")

    # Step 2: Groq analyzes Tavily results and extracts learning objectives
    themen = []
    if groq_key:
        try:
            from groq import Groq
            groq_client = Groq(api_key=groq_key)
            context = "\n\n".join(
                f"[{i+1}] {r['title']}: {r['content']}" for i, r in enumerate(tavily_results)
            )
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Du bist ein Lehrplan-Experte. Extrahiere aus den Suchergebnissen "
                            "50 konkrete Lernziele/Themen für das Fach. "
                            "Antworte NUR mit einem JSON Array von Strings."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Fach: {fach}, Bundesland: {bundesland}\n\n"
                            f"Suchergebnisse:\n{context}\n\n"
                            "Extrahiere 50 konkrete Lernziele als JSON Array."
                        ),
                    },
                ],
                max_tokens=2000,
                temperature=0.3,
            )
            content = resp.choices[0].message.content or "[]"
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            themen = json.loads(content)
        except Exception as e:
            logger.error("Groq themen extraction failed: %s", e)

    if not themen:
        raise HTTPException(status_code=502, detail="Konnte keine Themen extrahieren")

    # Step 3: Save to DB
    try:
        await db.execute(
            """INSERT OR REPLACE INTO lehrplan_themen (fach, bundesland, themen, quelle, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))""",
            (
                fach,
                bundesland,
                json.dumps(themen, ensure_ascii=False),
                json.dumps([r["url"] for r in tavily_results], ensure_ascii=False),
            ),
        )
        await db.commit()
    except Exception as e:
        logger.error("Could not save lehrplan themen: %s", e)

    return {
        "fach": fach,
        "bundesland": bundesland,
        "themen_count": len(themen),
        "themen_preview": themen[:10],
        "quellen": [r["url"] for r in tavily_results],
    }


@router.get("/lehrplan-themen")
async def get_lehrplan_themen(
    fach: str = "",
    bundesland: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get cached lehrplan themen for a subject/state combination."""
    import json
    conditions = []
    params: list = []
    if fach:
        conditions.append("fach = ?")
        params.append(fach)
    if bundesland:
        conditions.append("bundesland = ?")
        params.append(bundesland)

    where = " AND ".join(conditions) if conditions else "1=1"
    cursor = await db.execute(
        f"SELECT fach, bundesland, themen, quelle, updated_at FROM lehrplan_themen WHERE {where} ORDER BY updated_at DESC LIMIT 50",
        tuple(params),
    )
    rows = await cursor.fetchall()
    results = []
    for r in rows:
        rd = dict(r)
        try:
            rd["themen"] = json.loads(rd.get("themen", "[]"))
            rd["quelle"] = json.loads(rd.get("quelle", "[]"))
        except Exception:
            pass
        results.append(rd)
    return {"results": results}


@router.get("/monitoring-config")
async def monitoring_config():
    """Return monitoring configuration for the frontend."""
    return get_monitoring_frontend_config()


# ─── LUMNOS Self-Evolution Endpoints ───

class TriggerCrawlRequest(BaseModel):
    fach: str
    thema: str


@router.get("/knowledge-updates")
async def get_knowledge_updates(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Heutige Knowledge-Updates für das Admin-Dashboard."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    cursor = await db.execute(
        """SELECT id, fach, thema, quellen_count, created_at
        FROM knowledge_updates
        WHERE DATE(created_at) >= DATE('now', '-1 day')
        ORDER BY created_at DESC
        LIMIT 50"""
    )
    rows = await cursor.fetchall()
    return {"updates": [dict(r) for r in rows]}


@router.get("/prompt-vorschlaege")
async def get_prompt_vorschlaege(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Ausstehende Prompt-Vorschläge für Admin-Review."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    cursor = await db.execute(
        """SELECT id, fach, probleme, neuer_prompt, feedback_count,
               status, created_at, genehmigt_am
        FROM prompt_vorschlaege
        ORDER BY
            CASE WHEN status = 'ausstehend' THEN 0 ELSE 1 END,
            created_at DESC
        LIMIT 50"""
    )
    rows = await cursor.fetchall()
    return {"vorschlaege": [dict(r) for r in rows]}


@router.post("/trigger-crawl")
async def trigger_crawl(
    req: TriggerCrawlRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Manuellen Crawl für ein Fach/Thema auslösen."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    try:
        from app.services.deep_crawler import tavily_deep_search, synthesize_and_store
        docs = await tavily_deep_search(req.thema, req.fach)
        count = await synthesize_and_store(docs, req.fach, req.thema)

        # In DB loggen
        await db.execute(
            """INSERT INTO knowledge_updates (fach, thema, quellen_count)
            VALUES (?, ?, ?)""",
            (req.fach, req.thema, count),
        )
        await db.commit()

        return {
            "message": f"Crawl abgeschlossen: {count} Quellen für {req.fach}/{req.thema}",
            "fach": req.fach,
            "thema": req.thema,
            "quellen_count": count,
        }
    except Exception as e:
        logger.error("Manueller Crawl fehlgeschlagen: %s", e)
        raise HTTPException(status_code=500, detail=f"Crawl fehlgeschlagen: {e}")


@router.post("/prompts/{vorschlag_id}/genehmigen")
async def approve_prompt(
    vorschlag_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Admin genehmigt einen Prompt-Vorschlag."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    try:
        from app.services.prompt_optimizer import prompt_genehmigen
        success = await prompt_genehmigen(vorschlag_id)
        if success:
            return {"message": f"Prompt-Vorschlag {vorschlag_id} genehmigt und aktiviert"}
        raise HTTPException(status_code=404, detail="Vorschlag nicht gefunden")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Prompt genehmigen fehlgeschlagen: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolution-stats")
async def get_evolution_stats(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Statistiken für die Forschungs-Seite."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    stats: dict = {}

    # Positives/Negatives Feedback heute
    try:
        cursor = await db.execute(
            """SELECT bewertung, COUNT(*) as cnt
            FROM chat_feedbacks_v2
            WHERE DATE(created_at) >= DATE('now', '-1 day')
            GROUP BY bewertung"""
        )
        rows = await cursor.fetchall()
        fb = {dict(r)["bewertung"]: dict(r)["cnt"] for r in rows}
        stats["positiv_heute"] = fb.get("positiv", 0)
        stats["negativ_heute"] = fb.get("negativ", 0)
        total = stats["positiv_heute"] + stats["negativ_heute"]
        stats["qualitätsrate"] = round(
            stats["positiv_heute"] / total * 100, 1
        ) if total > 0 else 100.0
    except Exception:
        stats["positiv_heute"] = 0
        stats["negativ_heute"] = 0
        stats["qualitätsrate"] = 100.0

    # Neue Quellen heute
    try:
        cursor = await db.execute(
            """SELECT COALESCE(SUM(quellen_count), 0) as total
            FROM knowledge_updates
            WHERE DATE(created_at) >= DATE('now', '-1 day')"""
        )
        row = await cursor.fetchone()
        stats["neue_quellen"] = dict(row)["total"] if row else 0
    except Exception:
        stats["neue_quellen"] = 0

    # Ausstehende Vorschläge
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM prompt_vorschlaege WHERE status = 'ausstehend'"
        )
        row = await cursor.fetchone()
        stats["ausstehende_vorschlaege"] = row[0] if row else 0
    except Exception:
        stats["ausstehende_vorschlaege"] = 0

    # Updates pro Fach (für Orbs)
    try:
        cursor = await db.execute(
            """SELECT fach, COUNT(*) as cnt
            FROM knowledge_updates
            GROUP BY fach
            ORDER BY cnt DESC"""
        )
        rows = await cursor.fetchall()
        stats["fach_updates"] = {dict(r)["fach"]: dict(r)["cnt"] for r in rows}
    except Exception:
        stats["fach_updates"] = {}

    return stats
