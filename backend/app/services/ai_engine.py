import subprocess
import tempfile
import os
import threading
import time
from app.config import LLAMA_CPP_PATH, MODEL_PATH
from app.utils.logger import logger

class AIEngine:
    def __init__(self):
        self.model_path = MODEL_PATH
        self.llama_path = LLAMA_CPP_PATH
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        if not os.path.isfile(self.model_path):
            return False
        size = os.path.getsize(self.model_path)
        return size > 1024

    def rewrite(self, caption: str, prompt_template: str, new_price: int | None = None) -> str:
        if not self.is_available():
            logger.warning("Model not found at %s", self.model_path)
            return caption

        with self._lock:
            return self._rewrite_locked(caption, prompt_template, new_price)

    def _rewrite_locked(self, caption: str, prompt_template: str, new_price: int | None = None) -> str:
        system_prompt = prompt_template or (
            "Rewrite this reseller caption. "
            "Keep all specifications. Keep emojis. "
            "Remove supplier contact details. "
            "Replace old price with new price if provided. "
            "Add: Shipping Available. "
            "Do not change product details."
        )

        user_input = caption
        if new_price:
            user_input += f"\n\nNew Price: ₹{new_price}"

        full_prompt = f"<|system|>{system_prompt}</s>\n<|user|>{user_input}</s>\n<|assistant|>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(full_prompt)
            prompt_file = f.name

        try:
            t0 = time.time()
            result = subprocess.run(
                [
                    self.llama_path, "-m", self.model_path,
                    "-f", prompt_file,
                    "-n", "192",
                    "--temp", "0.7",
                    "--threads", "4",
                    "--no-mmap",
                    "-ngl", "0",
                ],
                capture_output=True, text=True, timeout=120,
            )
            elapsed = time.time() - t0
            output = result.stdout.strip()
            if output:
                logger.info("AI rewrite done in %.1fs (len=%d)", elapsed, len(output))
                return output
            return caption
        except subprocess.TimeoutExpired:
            logger.error("AI rewrite timed out after 120s")
            return caption
        except FileNotFoundError:
            logger.error("llama.cpp not found at %s", self.llama_path)
            return caption
        except Exception as e:
            logger.error("AI rewrite failed: %s", e)
            return caption
        finally:
            try:
                os.unlink(prompt_file)
            except OSError:
                pass

ai_engine = AIEngine()
