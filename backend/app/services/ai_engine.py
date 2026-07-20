import json
import time
import urllib.request
import urllib.error

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.utils.logger import logger

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

DEFAULT_PROMPT = """You are a WhatsApp product post editor.

MARKUP = {markup}

TASK

Edit the supplied WhatsApp product post by following these rules exactly.

RULES

1. Find the MAIN SELLING PRICE.
   The main selling price is usually:
   - The only product price in the post.
   - The price after words like Price, Rs, Rate, Available, Available@, Only.
   - The primary selling price of the product.

2. Ignore prices related to:
   - Shipping
   - OG Box
   - Indian Box
   - Accessories
   - Dust Cover
   - Invoice
   - Extra Charges
   - Any optional add-ons

3. Extract only the numeric value of the main selling price.
   Examples:
   2250
   4,799
   7500
   950

4. Remove commas from the number if present.

5. Add MARKUP to the extracted price.

6. Replace ONLY the main selling price with the calculated price.

7. Preserve the original price format.
   Examples:

   Price : 4,799
   → Price : 5799

   Price - 2250/- Only
   → Price - 3250/- Only

   Price 950 plus shipping
   → Price 1950 plus shipping

   Available@Rs 7500/-Plus shipping
   → Available@Rs 8500/-Plus shipping

   3000/-Rate
   → 4000/-Rate

8. Remove every line that contains any of the following:
   - http
   - https
   - www
   - Place Orders
   - Product Direct Link
   - Order Here
   - Buy Now
   - Checkout
   - Cart
   - Store Link

9. Remove any empty blank lines created after deleting text.

10. Append this footer exactly:

━━━━━━━━━━━━━━
🔥 Perfect Deals 🔥
Premium Quality Products
📦 Pan India Shipping

WhatsApp:
+918169858589
https://chat.whatsapp.com/Khx2ym45DSy1AXfp3XtY86

Posted by |NotJerry|
━━━━━━━━━━━━━━

11. Do NOT change:
   - Product title
   - Brand name
   - Description
   - Features
   - Specifications
   - Size
   - Quality
   - Emojis
   - Hashtags
   - Formatting
   - Existing line breaks (except removing blank lines)

12. Return ONLY the final edited WhatsApp post."""


class AIEngine:
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.model = GROQ_MODEL

    def is_available(self) -> bool:
        return bool(self.api_key)

    def rewrite(self, caption: str, prompt_template: str = None, markup: int = 1000) -> str:
        if not self.is_available():
            logger.warning("AI not available: GROQ_API_KEY not set")
            return caption
        try:
            system_prompt = (prompt_template or DEFAULT_PROMPT).format(markup=markup)
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": caption},
                ],
                "max_tokens": 512,
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
