from fastapi import APIRouter
from app.database.connection import get_connection

router = APIRouter()

@router.get("/status")
def get_status():
    conn = get_connection()
    ws = conn.execute("SELECT status, phone_number FROM whatsapp_sessions ORDER BY id DESC LIMIT 1").fetchone()
    products_today = conn.execute(
        "SELECT COUNT(*) FROM products WHERE date(created_at) = date('now')"
    ).fetchone()[0]
    products_posted = conn.execute(
        "SELECT COUNT(*) FROM products WHERE status = 'posted' AND date(created_at) = date('now')"
    ).fetchone()[0]
    queue_pending = conn.execute(
        "SELECT COUNT(*) FROM queue WHERE status = 'queued'"
    ).fetchone()[0]
    conn.close()

    phone = ws["phone_number"] if ws else None
    ws_status = ws["status"] if ws else "disconnected"

    return {
        "whatsapp_status": ws_status,
        "connected_number": phone,
        "products_today": products_today,
        "products_posted": products_posted,
        "pending_queue": queue_pending,
    }
