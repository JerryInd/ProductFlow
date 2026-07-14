import json
import urllib.request
import urllib.parse
from app.utils.logger import logger

TELEGRAM_API = "https://api.telegram.org"


class TelegramService:
    def __init__(self):
        self.bot_token = None
        self.bot_username = None
        self.bot_name = None

    def _api_url(self, method: str) -> str:
        return f"{TELEGRAM_API}/bot{self.bot_token}/{method}"

    def _request(self, method: str, params: dict | None = None) -> dict | None:
        try:
            url = self._api_url(method)
            if params:
                data = urllib.parse.urlencode(params).encode()
                req = urllib.request.Request(url, data=data, method="POST")
            else:
                req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                if result.get("ok"):
                    return result.get("result")
                else:
                    logger.error("Telegram API error: %s", result.get("description"))
                    return None
        except Exception as e:
            logger.error("Telegram request failed: %s", e)
            return None

    def verify_token(self, token: str) -> dict | None:
        self.bot_token = token
        result = self._request("getMe")
        if result:
            self.bot_username = result.get("username")
            self.bot_name = result.get("first_name")
            return {
                "bot_username": result.get("username"),
                "bot_name": result.get("first_name"),
                "bot_id": result.get("id"),
            }
        return None

    def set_webhook(self, url: str) -> bool:
        result = self._request("setWebhook", {"url": url})
        return result is not None

    def delete_webhook(self) -> bool:
        result = self._request("deleteWebhook")
        return result is not None

    def send_message(self, chat_id: str, text: str) -> bool:
        result = self._request("sendMessage", {
            "chat_id": chat_id,
            "text": text,
        })
        return result is not None

    def send_photo(self, chat_id: str, photo_path: str, caption: str = "") -> bool:
        try:
            import mimetypes
            boundary = "----FormBoundary7MA4YWxkTrZu0gW"
            body = b""

            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'.encode()
            body += f"{chat_id}\r\n".encode()

            if caption:
                body += f"--{boundary}\r\n".encode()
                body += f'Content-Disposition: form-data; name="caption"\r\n\r\n'.encode()
                body += f"{caption}\r\n".encode()

            filename = photo_path.split("/")[-1].split("\\")[-1]
            mime = mimetypes.guess_type(filename)[0] or "image/jpeg"

            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode()
            body += f"Content-Type: {mime}\r\n\r\n".encode()
            with open(photo_path, "rb") as f:
                body += f.read()
            body += b"\r\n"

            body += f"--{boundary}--\r\n".encode()

            url = self._api_url("sendPhoto")
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                return result.get("ok", False)
        except Exception as e:
            logger.error("Telegram send_photo failed: %s", e)
            return False

    def send_video(self, chat_id: str, video_path: str, caption: str = "") -> bool:
        try:
            import mimetypes
            boundary = "----FormBoundary7MA4YWxkTrZu0gW"
            body = b""

            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'.encode()
            body += f"{chat_id}\r\n".encode()

            if caption:
                body += f"--{boundary}\r\n".encode()
                body += f'Content-Disposition: form-data; name="caption"\r\n\r\n'.encode()
                body += f"{caption}\r\n".encode()

            filename = video_path.split("/")[-1].split("\\")[-1]
            mime = mimetypes.guess_type(filename)[0] or "video/mp4"

            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="video"; filename="{filename}"\r\n'.encode()
            body += f"Content-Type: {mime}\r\n\r\n".encode()
            with open(video_path, "rb") as f:
                body += f.read()
            body += b"\r\n"

            body += f"--{boundary}--\r\n".encode()

            url = self._api_url("sendVideo")
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return result.get("ok", False)
        except Exception as e:
            logger.error("Telegram send_video failed: %s", e)
            return False


telegram_service = TelegramService()
