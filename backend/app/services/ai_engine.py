import json
import time
import urllib.request
import urllib.error

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.utils.logger import logger

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class AIEngine:
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.model = GROQ_MODEL

    def is_available(self) -> bool:
        return bool(self.api_key)

    def rewrite(self, caption: str, prompt_template: str, new_price: str = None) -> str:
        if not self.is_available():
            logger.warning("AI not available: GROQ_API_KEY not set")
            return caption
        try:
            system_prompt = prompt_template or (
                "Rewrite product captions for a WhatsApp reseller. Rules:\n"
                "- Keep all product details (name, size, color, specs)\n"
                "- Remove supplier contacts, group invites, phone numbers\n"
                "- If a new price is given, replace the old price\n"
                "- Add 'Shipping Available.' at the end\n"
                "- Do NOT include labels like 'Rewritten:' or explanations\n"
                "- Output ONLY the rewritten caption"
            )
            user_input = caption
            if new_price:
                user_input += f"\n\nNew Price: Rs.{new_price}"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                "max_tokens": 256,
                "temperature": 0.3,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                GROQ_API_URL,
                data=data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "ProductFlow/1.0",
                },
            )
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            output = result["choices"][0]["message"]["content"].strip()
            if output:
                logger.info("AI rewrite done in %.1fs (len=%d, model=%s)", elapsed, len(output), self.model)
                return output
            logger.warning("AI returned empty output")
            return caption
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            logger.error("AI API error %d: %s", e.code, body)
            return caption
        except Exception as e:
            logger.error("AI rewrite failed: %s", e)
            return caption


ai_engine = AIEngine()
