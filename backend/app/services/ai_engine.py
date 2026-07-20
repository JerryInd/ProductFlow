import os
import subprocess
import time

from app.config import MODEL_PATH, LLAMA_CPP_PATH, LLAMA_CPP_DIR
from app.utils.logger import logger


class AIEngine:
    def __init__(self):
        self.model_path = MODEL_PATH
        self.llama_cli = LLAMA_CPP_PATH
        self.llama_dir = LLAMA_CPP_DIR

    def is_available(self) -> bool:
        binary = os.path.join(self.llama_dir, self.llama_cli)
        return os.path.isfile(binary) and os.path.isfile(self.model_path)

    def rewrite(self, caption: str, prompt_template: str, new_price: str = None) -> str:
        if not self.is_available():
            logger.warning("AI not available: llama-cli=%s model=%s", self.llama_cli, self.model_path)
            return caption
        try:
            system_prompt = prompt_template or (
                "You are a product caption rewriter for a reseller. "
                "Given a WhatsApp product caption, rewrite it to be clean and professional. "
                "Keep all specifications, sizes, colors, emojis. "
                "Remove supplier contact details and group invites. "
                "Replace old price with new price if provided. "
                "Add 'Shipping Available.' at the end. "
                "Output ONLY the rewritten caption, nothing else."
            )
            user_input = caption
            if new_price:
                user_input += f"\n\nNew Price: Rs.{new_price}"
            prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_input}\n<|assistant|>\n"
            binary = os.path.join(self.llama_dir, self.llama_cli)
            t0 = time.time()
            result = subprocess.run(
                [
                    binary,
                    "-m", self.model_path,
                    "-p", prompt,
                    "-n", "256",
                    "-t", "2",
                    "--ctx-size", "512",
                    "--temp", "0.7",
                    "--no-mmap",
                    "--no-display-prompt",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.llama_dir,
            )
            elapsed = time.time() - t0
            output = result.stdout.strip()
            if output:
                logger.info("AI rewrite done in %.1fs (len=%d)", elapsed, len(output))
                return output
            logger.warning("AI returned empty output, stderr: %s", result.stderr[:200])
            return caption
        except subprocess.TimeoutExpired:
            logger.error("AI rewrite timed out after 120s")
            return caption
        except Exception as e:
            logger.error("AI rewrite failed: %s", e)
            return caption


ai_engine = AIEngine()
