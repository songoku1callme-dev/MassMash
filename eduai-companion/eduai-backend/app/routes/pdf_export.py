"""PDF Export routes.

Supreme 10.0 Phase 13: Export notes and study plans as PDF.
"""
import io
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


def _generate_simple_pdf(title: str, content: str, author: str = "EduAI") -> io.BytesIO:
    """Generate a simple PDF from text content.

    Uses a basic approach that doesn't require heavy dependencies.
    """
    # Simple PDF generation using minimal approach
    pdf_buffer = io.BytesIO()

    # Clean content for PDF
    lines = content.split("\n")
    text_objects = []
    y_pos = 750

    # PDF header
    pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj

3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>
endobj

5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>
endobj

6 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>
endobj

"""
    # Build page content stream
    stream_lines = []
    stream_lines.append("BT")
    # Title
    stream_lines.append(f"/F1 18 Tf")
    stream_lines.append(f"50 750 Td")
    safe_title = title.replace("(", "\\(").replace(")", "\\)")
    stream_lines.append(f"({safe_title}) Tj")
    # Author + date
    stream_lines.append(f"/F2 10 Tf")
    stream_lines.append(f"0 -25 Td")
    date_str = datetime.now().strftime("%d.%m.%Y")
    stream_lines.append(f"(Erstellt von {author} am {date_str} | EduAI Companion) Tj")
    stream_lines.append(f"0 -15 Td")
    stream_lines.append(f"(---) Tj")
    # Content lines
    stream_lines.append(f"/F2 11 Tf")
    stream_lines.append(f"0 -20 Td")

    for line in lines[:50]:  # Limit to 50 lines per page
        safe_line = line.replace("(", "\\(").replace(")", "\\)").replace("\\", "\\\\")
        # Truncate long lines
        if len(safe_line) > 90:
            safe_line = safe_line[:87] + "..."
        stream_lines.append(f"0 -14 Td")
        stream_lines.append(f"({safe_line}) Tj")

    stream_lines.append("ET")
    stream_content = "\n".join(stream_lines)

    pdf_content += f"""4 0 obj
<< /Length {len(stream_content)} >>
stream
{stream_content}
endstream
endobj

xref
0 7
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000499 00000 n 
0000000266 00000 n 
0000000383 00000 n 

trailer
<< /Size 7 /Root 1 0 R >>
startxref
{len(pdf_content) + len(stream_content) + 50}
%%EOF"""

    pdf_buffer.write(pdf_content.encode("latin-1", errors="replace"))
    pdf_buffer.seek(0)
    return pdf_buffer


@router.get("/notizen/{notiz_id}/pdf")
async def export_note_pdf(
    notiz_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Export a note as PDF."""
    user_id = current_user["id"]

    # Notes are stored in activity_log with type 'note'
    cursor = await db.execute(
        """SELECT description, metadata, created_at FROM activity_log
        WHERE id = ? AND user_id = ? AND activity_type IN ('note_created', 'note')""",
        (notiz_id, user_id),
    )
    note = await cursor.fetchone()
    if not note:
        raise HTTPException(status_code=404, detail="Notiz nicht gefunden")

    nd = dict(note)
    title = nd["description"][:50] if nd["description"] else "Notiz"
    content = nd["description"]

    try:
        meta = json.loads(nd["metadata"])
        if "content" in meta:
            content = meta["content"]
        if "title" in meta:
            title = meta["title"]
    except Exception:
        pass

    pdf_buffer = _generate_simple_pdf(title, content, current_user.get("username", "Schueler"))

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=EduAI_{title[:30]}.pdf"},
    )


@router.get("/lernplan/pdf")
async def export_lernplan_pdf(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Export the user's weekly learning plan as PDF."""
    user_id = current_user["id"]

    # Get weak topics
    cursor = await db.execute(
        """SELECT subject, topic_name FROM user_memories
        WHERE user_id = ? AND schwach = 1 ORDER BY feedback_score ASC LIMIT 10""",
        (user_id,),
    )
    weak_rows = await cursor.fetchall()

    # Get gamification stats
    cursor = await db.execute(
        "SELECT xp, level, level_name, streak_days FROM gamification WHERE user_id = ?",
        (user_id,),
    )
    g_row = await cursor.fetchone()
    gd = dict(g_row) if g_row else {"xp": 0, "level": 1, "level_name": "Neuling", "streak_days": 0}

    # Build plan content
    lines = [
        f"Level: {gd['level']} ({gd['level_name']})",
        f"XP: {gd['xp']} | Streak: {gd['streak_days']} Tage",
        "",
        "Schwache Themen:",
    ]

    for row in weak_rows:
        rd = dict(row)
        lines.append(f"  - {rd['subject']}: {rd['topic_name']}")

    if not weak_rows:
        lines.append("  Keine Schwaechen erkannt. Weiter so!")

    lines.extend([
        "",
        "Empfohlener Wochenplan:",
        "  Mo: Quiz + Karteikarten (schwaches Fach)",
        "  Di: 2 Pomodoro-Sessions + Chat mit KI",
        "  Mi: Abitur-Simulation (1 Fach)",
        "  Do: Multiplayer-Quiz + Gruppenlernen",
        "  Fr: Wissensscan + Feynman-Technik",
        "  Sa: Turnier + Wiederholung",
        "  So: Entspannung + leichte Wiederholung",
    ])

    username = current_user.get("username", "Schueler")
    pdf_buffer = _generate_simple_pdf(f"Lernplan fuer {username}", "\n".join(lines), username)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=EduAI_Lernplan_{username}.pdf"},
    )
