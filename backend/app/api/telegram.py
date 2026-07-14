from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.connection import get_connection
from app.services.telegram_service import telegram_service
from app.utils.helpers import serialize_row
from app.utils.logger import logger

router = APIRouter()


class TokenBody(BaseModel):
    bot_token: str


class WebhookBody(BaseModel):
    url: str


class TelegramStatus(BaseModel):
    status: str
    bot_username: str | None = None
    bot_name: str | None = None


@router.get("/status")
def get_status():
    conn = get_connection()
    row = conn.execute(
        "SELECT status, bot_username, bot_name FROM telegram_sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return TelegramStatus(
            status=row["status"],
            bot_username=row["bot_username"],
            bot_name=row["bot_name"],
        )
    return TelegramStatus(status="disconnected")


@router.post("/connect")
def connect(body: TokenBody):
    result = telegram_service.verify_token(body.bot_token)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid bot token. Get one from @BotFather on Telegram.")

    conn = get_connection()
    existing = conn.execute("SELECT id FROM telegram_sessions ORDER BY id DESC LIMIT 1").fetchone()
    if existing:
        conn.execute(
            """UPDATE telegram_sessions
               SET bot_token = ?, bot_username = ?, bot_name = ?, status = 'connected', updated_at = datetime('now')
               WHERE id = ?""",
            (body.bot_token, result["bot_username"], result["bot_name"], existing["id"]),
        )
    else:
        conn.execute(
            """INSERT INTO telegram_sessions (bot_token, bot_username, bot_name, status)
               VALUES (?, ?, ?, 'connected')""",
            (body.bot_token, result["bot_username"], result["bot_name"]),
        )
    conn.commit()
    conn.close()

    telegram_service.bot_token = body.bot_token
    telegram_service.bot_username = result["bot_username"]
    telegram_service.bot_name = result["bot_name"]

    logger.info("Telegram connected: @%s (%s)", result["bot_username"], result["bot_name"])
    return {"message": "Connected", "bot_username": result["bot_username"], "bot_name": result["bot_name"]}


@router.post("/disconnect")
def disconnect():
    conn = get_connection()
    conn.execute(
        "UPDATE telegram_sessions SET status = 'disconnected', updated_at = datetime('now')"
    )
    conn.commit()
    conn.close()
    telegram_service.bot_token = None
    telegram_service.bot_username = None
    telegram_service.bot_name = None
    return {"message": "Disconnected"}


@router.post("/webhook")
def set_webhook(body: WebhookBody):
    ok = telegram_service.set_webhook(body.url)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to set webhook")
    conn = get_connection()
    conn.execute(
        "UPDATE telegram_sessions SET webhook_url = ?, updated_at = datetime('now')",
        (body.url,),
    )
    conn.commit()
    conn.close()
    return {"message": "Webhook set"}


@router.post("/incoming")
def handle_incoming(data: dict):
    message = data.get("message") or data.get("channel_post")
    if not message:
        return {"ok": True}

    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "")
    from_user = message.get("from", {}).get("username", "")

    logger.info("Telegram message from %s in %s: %s", from_user, chat_id, text[:50])

    conn = get_connection()
    sources = conn.execute(
        """SELECT ps.pipeline_id, ps.group_id FROM pipeline_sources ps
           JOIN pipelines p ON p.id = ps.pipeline_id
           WHERE ps.group_id = ? AND p.enabled = 1""",
        (chat_id,),
    ).fetchall()
    conn.close()

    if not sources:
        return {"ok": True}

    for source in sources:
        pid = source["pipeline_id"]
        _process_telegram_message(pid, chat_id, message)

    return {"ok": True}


def _process_telegram_message(pipeline_id: int, chat_id: str, message: dict):
    from app.services.pipeline_service import pipeline_service

    text = message.get("text", "")
    photo = message.get("photo")
    video = message.get("video")
    document = message.get("document")

    if photo:
        largest = photo[-1] if photo else photo
        file_id = largest.get("file_id", "")
        msg_type = "image"
    elif video:
        file_id = video.get("file_id", "")
        msg_type = "video"
    elif text:
        file_id = ""
        msg_type = "text"
    else:
        return

    msg_data = {
        "id": str(message.get("message_id", "")),
        "type": msg_type,
        "text": text,
        "media_path": "",
        "from_": chat_id,
        "timestamp": message.get("date"),
        "file_id": file_id,
    }

    pipeline_service.process_message(pipeline_id, chat_id, msg_data)
