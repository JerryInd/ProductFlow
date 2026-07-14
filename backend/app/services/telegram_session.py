import os
import asyncio
import threading
import time
from pathlib import Path
from app.config import SESSIONS_DIR
from app.utils.logger import logger

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")

SESSION_FILE = os.path.join(SESSIONS_DIR, "telegram")


class TelegramSession:
    def __init__(self):
        self._client = None
        self._qr_code = None
        self._status = "disconnected"
        self._username = None
        self._phone = None
        self._thread = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()

    @property
    def status(self):
        with self._lock:
            return self._status

    @property
    def qr_code(self):
        with self._lock:
            return self._qr_code

    @property
    def username(self):
        with self._lock:
            return self._username

    @property
    def phone(self):
        with self._lock:
            return self._phone

    def _set_status(self, status):
        with self._lock:
            self._status = status

    def _set_qr(self, qr):
        with self._lock:
            self._qr_code = qr

    def is_session_file(self):
        return os.path.exists(SESSION_FILE + ".session")

    def start(self):
        if self._status in ("connecting", "connected", "qr_pending"):
            return
        self._stop_event.clear()
        self._connected_event.clear()
        self._set_status("connecting")
        self._set_qr(None)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._set_status("disconnected")
        self._set_qr(None)
        if self._client:
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._client.disconnect())
                loop.close()
            except Exception:
                pass
            self._client = None

    def _run(self):
        try:
            asyncio.run(self._connect())
        except Exception as e:
            logger.error("Telegram session error: %s", e)
            self._set_status("disconnected")
            self._set_qr(None)

    async def _connect(self):
        from pyrogram import Client

        os.makedirs(SESSIONS_DIR, exist_ok=True)

        self._client = Client(
            name=SESSION_FILE,
            api_id=TELEGRAM_API_ID,
            api_hash=TELEGRAM_API_HASH,
        )

        if self.is_session_file():
            try:
                await self._client.start()
                me = await self._client.get_me()
                self._username = me.username or me.first_name
                self._phone = me.phone_number
                self._set_status("connected")
                logger.info("Telegram session restored: @%s", self._username)
                self._connected_event.wait()
                return
            except Exception as e:
                logger.error("Telegram session restore failed: %s", e)
                self._delete_session_file()
                self._set_status("disconnected")
                return

        try:
            await self._client.connect()
        except Exception as e:
            logger.error("Telegram connect failed: %s", e)
            self._set_status("disconnected")
            return

        self._set_status("qr_pending")

        try:
            qr_url = await self._generate_qr()
            if qr_url:
                self._set_qr(qr_url)
                logger.info("Telegram QR generated")
        except Exception as e:
            logger.error("Telegram QR generation failed: %s", e)
            self._set_status("disconnected")
            return

        try:
            me = await self._wait_for_scan()
            if me:
                self._username = me.username or me.first_name
                self._phone = me.phone_number
                self._set_status("connected")
                self._set_qr(None)
                logger.info("Telegram connected: @%s", self._username)
                await self._client.invoke(
                    __import__("pyrogram.raw.functions.auth", fromlist=["ExportAuthorization"]).ExportAuthorization()
                )
                self._connected_event.wait()
            else:
                self._set_status("disconnected")
                self._set_qr(None)
        except Exception as e:
            logger.error("Telegram scan wait failed: %s", e)
            self._set_status("disconnected")
            self._set_qr(None)

    async def _generate_qr(self):
        from pyrogram.raw import functions, types

        result = await self._client.invoke(
            functions.auth.ExportLoginToken(
                api_id=TELEGRAM_API_ID,
                api_hash=TELEGRAM_API_HASH,
                except_types=[types.InputPhoneUser],
            )
        )

        if isinstance(result, types.auth.LoginToken):
            import base64
            qr_data = base64.urlsafe_b64encode(result.token).decode().rstrip("=")
            return f"https://oauth.telegram.org/auth?app_id={TELEGRAM_API_ID}&bot_auth_url=https%3A//productflow.pages.dev&scope=experimental&nols=6&request_access=write&token={qr_data}"

        return None

    async def _wait_for_scan(self):
        import time as _time
        from pyrogram.raw import functions, types

        start = _time.time()
        timeout = 120

        while _time.time() - start < timeout:
            if self._stop_event.is_set():
                return None

            try:
                result = await self._client.invoke(
                    functions.auth.ExportLoginToken(
                        api_id=TELEGRAM_API_ID,
                        api_hash=TELEGRAM_API_HASH,
                        except_types=[types.InputPhoneUser],
                    )
                )

                if isinstance(result, types.auth.LoginTokenSuccess):
                    me = await self._client.get_me()
                    return me
                elif isinstance(result, types.auth.LoginTokenMigrateTo):
                    return None

            except Exception:
                pass

            await asyncio.sleep(2)

        return None

    def _delete_session_file(self):
        for ext in (".session", ".session-journal"):
            path = SESSION_FILE + ext
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    async def send_message(self, chat_id: str, text: str) -> bool:
        if not self._client or self._status != "connected":
            return False
        try:
            await self._client.send_message(chat_id, text)
            return True
        except Exception as e:
            logger.error("Telegram send_message failed: %s", e)
            return False

    async def send_photo(self, chat_id: str, photo_path: str, caption: str = "") -> bool:
        if not self._client or self._status != "connected":
            return False
        try:
            await self._client.send_photo(chat_id, photo_path, caption=caption)
            return True
        except Exception as e:
            logger.error("Telegram send_photo failed: %s", e)
            return False

    async def send_video(self, chat_id: str, video_path: str, caption: str = "") -> bool:
        if not self._client or self._status != "connected":
            return False
        try:
            await self._client.send_video(chat_id, video_path, caption=caption)
            return True
        except Exception as e:
            logger.error("Telegram send_video failed: %s", e)
            return False

    async def get_dialogs(self):
        if not self._client or self._status != "connected":
            return []
        try:
            dialogs = []
            async for dialog in self._client.get_dialogs():
                if dialog.chat and dialog.chat.type in ("group", "supergroup", "channel"):
                    dialogs.append({
                        "id": str(dialog.chat.id),
                        "name": dialog.chat.title or "Unknown",
                        "type": str(dialog.chat.type),
                    })
            return dialogs
        except Exception as e:
            logger.error("Telegram get_dialogs failed: %s", e)
            return []


telegram_session = TelegramSession()
