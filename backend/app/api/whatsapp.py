import asyncio
import json
import urllib.request
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.database.connection import get_connection
from app.utils.helpers import serialize_row
from app.utils.logger import logger

router = APIRouter()

BRIDGE_URL = "http://localhost:8001"

class QRBody(BaseModel):
    qr: str
    qr_image: str | None = None

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

class RelayBody(BaseModel):
    group_name: str
    text: str = ""
    qr: str | None = None

@router.get("/qr")
def get_qr():
    conn = get_connection()
    row = conn.execute(
        "SELECT qr_code FROM whatsapp_sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row and row["qr_code"]:
        return {"qr": row["qr_code"], "qr_image": "/api/whatsapp/qr-image"}
    raise HTTPException(status_code=404, detail="No QR code available")


@router.get("/qr-image")
def get_qr_image():
    try:
        req = urllib.request.Request(f"{BRIDGE_URL}/qr-image")
        with urllib.request.urlopen(req, timeout=10) as resp:
            from fastapi.responses import Response
            return Response(content=resp.read(), media_type="image/png")
    except Exception as e:
        logger.error("Failed to fetch QR image from bridge: %s", e)
        raise HTTPException(status_code=502, detail="Bridge QR not available")

@router.post("/qr")
def set_qr(body: QRBody):
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM whatsapp_sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE whatsapp_sessions SET qr_code = ?, qr_image = ?, updated_at = datetime('now') WHERE id = ?",
            (body.qr, body.qr_image, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO whatsapp_sessions (session_name, qr_code, qr_image, status) VALUES (?, ?, ?, 'scanning')",
            ("productflow-session", body.qr, body.qr_image),
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
    logger.info("Incoming msg from=%s type=%s", body.from_, body.type)
    conn = get_connection()
    rows = conn.execute(
        """SELECT ps.pipeline_id FROM pipeline_sources ps
           JOIN pipelines p ON p.id = ps.pipeline_id
           WHERE ps.group_id = ? AND p.enabled = 1""",
        (body.from_,),
    ).fetchall()
    conn.close()

    if not rows:
        logger.info("No matching pipeline for group %s", body.from_)

    data = body.model_dump()
    for row in rows:
        pid = row["pipeline_id"]
        background_tasks.add_task(process_in_background, pid, body.from_, data)

    return {"message": "accepted"}


async def process_in_background(pipeline_id: int, source_group_id: str, message: dict):
    from app.services.pipeline_service import pipeline_service

    pipeline_service.process_message(pipeline_id, source_group_id, message)

@router.post("/relay")
async def handle_relay(body: RelayBody, background_tasks: BackgroundTasks):
    conn = get_connection()
    row = conn.execute(
        "SELECT group_id FROM groups WHERE group_name = ?",
        (body.group_name,),
    ).fetchone()
    conn.close()

    if not row:
        logger.warning("Relay: unknown group '%s'", body.group_name)
        return {"message": "ignored", "reason": "unknown group"}

    group_id = row["group_id"]
    logger.info("Relay msg from '%s' (%s) len=%d", body.group_name, group_id, len(body.text))

    conn = get_connection()
    rows = conn.execute(
        """SELECT ps.pipeline_id FROM pipeline_sources ps
           JOIN pipelines p ON p.id = ps.pipeline_id
           WHERE ps.group_id = ? AND p.enabled = 1""",
        (group_id,),
    ).fetchall()
    conn.close()

    if not rows:
        logger.info("Relay: no matching pipeline for group %s", group_id)
        return {"message": "ignored", "reason": "no pipeline"}

    import time
    msg_data = {
        "id": f"relay-{group_id}-{int(time.time()*1000)}",
        "type": "text",
        "text": body.text,
        "from_": group_id,
    }
    for r in rows:
        background_tasks.add_task(process_in_background, r["pipeline_id"], group_id, msg_data)

    return {"message": "accepted"}

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


class ForwardBody(BaseModel):
    product_ids: list[int]
    recipient: str  # phone number or JID

class ForwardResult(BaseModel):
    sent: int
    failed: int
    errors: list[str]


@router.get("/chats")
def get_chats():
    try:
        req = urllib.request.Request(f"{BRIDGE_URL}/chats")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return {"chats": data.get("chats", [])}
            return {"chats": []}
    except Exception as e:
        logger.error(f"Failed to fetch chats: {e}")
        return {"chats": []}


@router.post("/forward")
def forward_products(body: ForwardBody):
    conn = get_connection()
    products = []
    for pid in body.product_ids:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if row:
            products.append(serialize_row(row))
    conn.close()

    if not products:
        raise HTTPException(status_code=404, detail="No products found")

    sent = 0
    failed = 0
    errors = []

    for product in products:
        media_paths = json.loads(product.get("media_paths") or "[]")
        video_paths = json.loads(product.get("video_paths") or "[]")
        caption = product.get("rewritten_caption") or product.get("caption") or ""

        try:
            if media_paths:
                for mp in media_paths:
                    _bridge_send_media(body.recipient, mp, caption)
                    sent += 1
            elif video_paths:
                for vp in video_paths:
                    _bridge_send_media(body.recipient, vp, caption)
                    sent += 1
            else:
                _bridge_send_text(body.recipient, caption)
                sent += 1
        except Exception as e:
            failed += 1
            errors.append(str(e))

    return {"sent": sent, "failed": failed, "errors": errors}


def _bridge_send_text(recipient: str, text: str):
    data = json.dumps({"group_id": recipient, "text": text}).encode()
    req = urllib.request.Request(
        f"{BRIDGE_URL}/",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        if not result.get("ok"):
            raise Exception(result.get("error", "Send failed"))


def _bridge_send_media(recipient: str, media_path: str, caption: str = ""):
    data = json.dumps({
        "group_id": recipient,
        "media_path": media_path,
        "caption": caption,
    }).encode()
    req = urllib.request.Request(
        f"{BRIDGE_URL}/",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        if not result.get("ok"):
            raise Exception(result.get("error", "Send failed"))
