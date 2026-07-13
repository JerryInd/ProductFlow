import json
import urllib.request
from app.config import API_PORT
from app.utils.logger import logger

BRIDGE_URL = f"http://localhost:{8001}"


class WhatsAppService:
    def __init__(self):
        self.connected = False
        self.phone_number = None

    async def get_qr(self) -> str:
        logger.info("QR requested - WhatsApp service stub")
        return "placeholder-qr-code"

    async def connect(self, session_data: str | None = None):
        logger.info("WhatsApp connect requested")
        self.connected = True

    async def disconnect(self):
        logger.info("WhatsApp disconnect requested")
        self.connected = False

    async def send_message(self, group_id: str, text: str) -> bool:
        return await self._bridge_post({"group_id": group_id, "text": text})

    async def send_media(self, group_id: str, media_path: str, caption: str = "") -> bool:
        return await self._bridge_post({
            "group_id": group_id,
            "media_path": media_path,
            "caption": caption,
        })

    def is_connected(self) -> bool:
        return self.connected

    async def _bridge_post(self, data: dict) -> bool:
        try:
            req = urllib.request.Request(
                f"{BRIDGE_URL}/",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                return result.get("ok", False)
        except Exception as e:
            logger.error(f"Bridge request failed: {e}")
            return False


whatsapp_service = WhatsAppService()
