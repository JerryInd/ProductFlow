import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.database.connection import get_connection
from app.utils.helpers import serialize_row

router = APIRouter()

class QRBody(BaseModel):
    qr: str

class StatusBody(BaseModel):
    status: str
    phone_number: str | None = None

class MessageBody(BaseModel):
    id: str
    type: str
    text: str = ""
    media_path: str = ""
    from_: str = ""
    timestamp: int | None = None

class SessionStatus(BaseModel):
    status: str
    phone_number: str | None = None
    qr: str | None = None

@router.get("/qr")
def get_qr():
    conn = get_connection()
    row = conn.execute(
        "SELECT qr_code FROM whatsapp_sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row and row["qr_code"]:
        return {"qr": row["qr_code"]}
    raise HTTPException(status_code=404, detail="No QR code available")

@router.post("/qr")
def set_qr(body: QRBody):
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM whatsapp_sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE whatsapp_sessions SET qr_code = ?, updated_at = datetime('now') WHERE id = ?",
            (body.qr, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO whatsapp_sessions (session_name, qr_code, status) VALUES (?, ?, 'scanning')",
            ("productflow-session", body.qr),
        )
    conn.commit()
    conn.close()
    return {"message": "QR stored"}

@router.post("/status")
def update_status(body: StatusBody):
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM whatsapp_sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE whatsapp_sessions SET status = ?, phone_number = ?, updated_at = datetime('now') WHERE id = ?",
            (body.status, body.phone_number, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO whatsapp_sessions (session_name, status, phone_number) VALUES (?, ?, ?)",
            ("productflow-session", body.status, body.phone_number),
        )
    conn.commit()
    conn.close()
    return {"message": "Status updated"}

@router.post("/message")
async def handle_message(body: MessageBody, background_tasks: BackgroundTasks):
    conn = get_connection()
    rows = conn.execute(
        """SELECT ps.pipeline_id FROM pipeline_sources ps
           JOIN pipelines p ON p.id = ps.pipeline_id
           WHERE ps.group_id = ? AND p.enabled = 1""",
        (body.from_,),
    ).fetchall()
    conn.close()

    data = body.model_dump()
    for row in rows:
        pid = row["pipeline_id"]
        background_tasks.add_task(process_in_background, pid, body.from_, data)

    return {"message": "accepted"}


async def process_in_background(pipeline_id: int, source_group_id: str, message: dict):
    from app.services.pipeline_service import pipeline_service

    pipeline_service.process_message(pipeline_id, source_group_id, message)

@router.post("/connect")
def connect():
    raise HTTPException(status_code=501, detail="Use the bridge directly")

@router.post("/disconnect")
def disconnect():
    raise HTTPException(status_code=501, detail="Use the bridge directly")

@router.get("/status")
def status():
    conn = get_connection()
    row = conn.execute(
        "SELECT status, phone_number FROM whatsapp_sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return SessionStatus(status=row["status"], phone_number=row["phone_number"])
    return SessionStatus(status="disconnected")

@router.get("/session")
def get_session():
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM whatsapp_sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return serialize_row(row)
    return {"status": "disconnected"}
