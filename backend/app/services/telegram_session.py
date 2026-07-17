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
        self._loop = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

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
        logger.info("Telegram session status: %s", status)

    def _set_qr(self, qr):
        with self._lock:
            self._qr_code = qr

    def is_session_file(self):
        return os.path.exists(SESSION_FILE + ".session")

    def start(self):
        if self._status in ("connecting", "connected", "qr_pending"):
            return
        self._stop_event.clear()
        self._set_status("connecting")
        self._set_qr(None)
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._set_status("disconnected")
        self._set_qr(None)
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._cleanup(), self._loop)

    def _run_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            logger.info("Telegram thread starting event loop")
            self._loop.run_until_complete(self._connect())
            logger.info("Telegram thread connect coroutine completed")
        except Exception as e:
            logger.error("Telegram thread error: %s", e, exc_info=True)
            self._set_status("disconnected")
            self._set_qr(None)
        finally:
            self._loop.close()
            self._loop = None

    async def _cleanup(self):
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None

    async def _connect(self):
        from pyrogram import Client
        from pyrogram.raw import functions, types
        import base64

        os.makedirs(SESSIONS_DIR, exist_ok=True)

        self._client = Client(
            name=SESSION_FILE,
            api_id=TELEGRAM_API_ID,
            api_hash=TELEGRAM_API_HASH,
        )

        # Check if we have a valid session (file exists AND user_id is stored)
        has_valid_session = False
        if self.is_session_file():
            try:
                await self._client.load_session()
                user_id = await self._client.storage.user_id()
                has_valid_session = user_id is not None
            except Exception:
                pass

        if has_valid_session:
            try:
                await self._client.start()
                me = await self._client.get_me()
                self._username = me.username or me.first_name
                self._phone = me.phone_number
                self._set_status("connected")
                logger.info("Telegram session restored: @%s", self._username)
                while not self._stop_event.is_set():
                    await asyncio.sleep(1)
                await self._client.stop()
                return
            except Exception as e:
                logger.error("Telegram session restore failed: %s", e, exc_info=True)
                self._delete_session_file()
                self._client = Client(
                    name=SESSION_FILE,
                    api_id=TELEGRAM_API_ID,
                    api_hash=TELEGRAM_API_HASH,
                )

        # Fresh login — connect transport only (skip authorize)
        try:
            logger.info("Telegram calling client.connect()...")
            connected = await self._client.connect()
            logger.info("Telegram client.connect() returned: %s", connected)
        except Exception as e:
            logger.error("Telegram connect failed: %s", e, exc_info=True)
            self._set_status("disconnected")
            return

        self._set_status("qr_pending")
        logger.info("Telegram status set to qr_pending, calling ExportLoginToken...")

        try:
            result = await self._client.invoke(
                functions.auth.ExportLoginToken(
                    api_id=TELEGRAM_API_ID,
                    api_hash=TELEGRAM_API_HASH,
                    except_ids=[],
                )
            )

            if isinstance(result, types.auth.LoginToken):
                token = result.token
                token_b64 = base64.urlsafe_b64encode(token).decode().rstrip("=")
                qr_url = (
                    f"https://oauth.telegram.org/auth"
                    f"?app_id={TELEGRAM_API_ID}"
                    f"&bot_auth_url=https%3A//productflow.pages.dev"
                    f"&scope=experimental&nols=6&request_access=write"
                    f"&token={token_b64}"
                )
                self._set_qr(qr_url)
                logger.info("Telegram QR generated")
            else:
                logger.error("Telegram unexpected token type: %s", type(result))
                self._set_status("disconnected")
                return
        except Exception as e:
            logger.error("Telegram QR generation failed: %s", e)
            self._set_status("disconnected")
            return

        # Poll for scan using ExportLoginToken (re-export checks scan status)
        start = time.time()
        timeout = 300

        while time.time() - start < timeout:
            if self._stop_event.is_set():
                await self._client.disconnect()
                return

            await asyncio.sleep(3)

            try:
                result = await self._client.invoke(
                    functions.auth.ExportLoginToken(
                        api_id=TELEGRAM_API_ID,
                        api_hash=TELEGRAM_API_HASH,
                        except_ids=[],
                    )
                )

                if isinstance(result, types.auth.LoginTokenSuccess):
                    me = await self._client.get_me()
                    self._username = me.username or me.first_name
                    self._phone = me.phone_number
                    self._set_status("connected")
                    self._set_qr(None)
                    logger.info("Telegram QR login success: @%s", self._username)
                    while not self._stop_event.is_set():
                        await asyncio.sleep(1)
                    await self._client.stop()
                    return
                elif isinstance(result, types.auth.LoginTokenMigrateTo):
                    logger.info("Telegram migrating to DC %s", result.dc_id)
                    return
                elif isinstance(result, types.auth.LoginToken):
                    token = result.token
                    token_b64 = base64.urlsafe_b64encode(token).decode().rstrip("=")
                    new_qr = (
                        f"https://oauth.telegram.org/auth"
                        f"?app_id={TELEGRAM_API_ID}"
                        f"&bot_auth_url=https%3A//productflow.pages.dev"
                        f"&scope=experimental&nols=6&request_access=write"
                        f"&token={token_b64}"
                    )
                    self._set_qr(new_qr)

            except Exception as e:
                logger.error("Telegram scan poll error: %s", e)
                break

        logger.warning("Telegram QR login timed out")
        self._set_status("disconnected")
        self._set_qr(None)
        await self._client.disconnect()

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
