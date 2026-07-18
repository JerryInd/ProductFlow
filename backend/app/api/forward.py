import asyncio
import json
import os
import urllib.request
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.connection import get_connection
from app.services.telegram_session import telegram_session
from app.utils.helpers import serialize_row
from app.utils.logger import logger

router = APIRouter()

BRIDGE_URL = os.getenv("BRIDGE_URL", "http://127.0.0.1:8001")


class ChatItem(BaseModel):
    jid: str
    name: str
    platform: str  # "whatsapp" or "telegram"


class ForwardRecipient(BaseModel):
    platform: str
    jid: str


class ForwardBody(BaseModel):
    product_ids: list[int]
    recipients: list[ForwardRecipient]


class ForwardResult(BaseModel):
    sent: int
    failed: int
    errors: list[str]


@router.get("/chats")
async def get_chats():
    all_chats: list[ChatItem] = []

    try:
        req = urllib.request.Request(f"{BRIDGE_URL}/chats")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                for c in data.get("chats", []):
                    all_chats.append(ChatItem(
                        jid=c.get("jid", ""),
                        name=c.get("name") or c.get("jid", "").split("@")[0],
                        platform="whatsapp",
                    ))
    except Exception as e:
        logger.warning("Failed to fetch WhatsApp chats: %s", e)

    try:
        tg_dialogs = await telegram_session.get_dialogs()
        for d in tg_dialogs:
            all_chats.append(ChatItem(
                jid=d["id"],
                name=d["name"],
                platform="telegram",
            ))
    except Exception as e:
        logger.warning("Failed to fetch Telegram dialogs: %s", e)

    return {"chats": all_chats}


@router.post("/forward")
async def forward_products(body: ForwardBody):
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

    for recipient in body.recipients:
        for product in products:
            caption = product.get("rewritten_caption") or product.get("caption") or ""
            media_paths = []
            if product.get("media_paths"):
                try:
                    media_paths = json.loads(product["media_paths"]) if isinstance(product["media_paths"], str) else product["media_paths"]
                except Exception:
                    pass
            if product.get("video_paths"):
                try:
                    vps = json.loads(product["video_paths"]) if isinstance(product["video_paths"], str) else product["video_paths"]
                    media_paths.extend(vps)
                except Exception:
                    pass

            try:
                if recipient.platform == "whatsapp":
                    ok = _send_whatsapp(recipient.jid, media_paths, caption)
                elif recipient.platform == "telegram":
                    ok = await _send_telegram(recipient.jid, media_paths, caption)
                else:
                    ok = False
                    errors.append(f"Unknown platform: {recipient.platform}")

                if ok:
                    sent += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                errors.append(str(e))

    return ForwardResult(sent=sent, failed=failed, errors=errors)


def _send_whatsapp(jid: str, media_paths: list, caption: str) -> bool:
    try:
        if media_paths:
            data = json.dumps({"jid": jid, "path": media_paths[0], "caption": caption}).encode()
        else:
            data = json.dumps({"jid": jid, "text": caption}).encode()
        endpoint = "/sendMedia" if media_paths else "/sendMessage"
        req = urllib.request.Request(
            f"{BRIDGE_URL}{endpoint}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        logger.error("WhatsApp forward failed: %s", e)
        return False


async def _send_telegram(chat_id: str, media_paths: list, caption: str) -> bool:
    try:
        if media_paths:
            path = media_paths[0]
            ext = os.path.splitext(path)[1].lower()
            if ext in (".mp4", ".mov", ".avi", ".webm"):
                return await telegram_session.send_video(chat_id, path, caption=caption)
            else:
                return await telegram_session.send_photo(chat_id, path, caption=caption)
        else:
            return await telegram_session.send_message(chat_id, caption)
    except Exception as e:
        logger.error("Telegram forward failed: %s", e)
        return False
