import os
import re
import subprocess
import tempfile
import time

from app.config import MODEL_PATH, LLAMA_CPP_DIR
from app.utils.logger import logger


class AIEngine:
    def __init__(self):
        self.model_path = MODEL_PATH
        self.llama_dir = LLAMA_CPP_DIR
        self.llama_cli = "llama-completion"

    def is_available(self) -> bool:
        binary = os.path.join(self.llama_dir, self.llama_cli)
        return os.path.isfile(binary) and os.path.isfile(self.model_path)

    def rewrite(self, caption: str, prompt_template: str, new_price: str = None) -> str:
        if not self.is_available():
            logger.warning("AI not available: model=%s", self.model_path)
            return caption
        try:
            system_prompt = prompt_template or (
                "Rewrite this product caption. Keep details, remove contacts. "
                "Add Shipping Available. Output only the caption."
            )
            user_input = caption
            if new_price:
                user_input += f"\nNew Price: Rs.{new_price}"
            prompt = f"System: {system_prompt}\nProduct: {user_input}\nRewritten:"
            binary = os.path.join(self.llama_dir, self.llama_cli)
            t0 = time.time()
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, dir="/tmp") as f:
                f.write(prompt)
                prompt_file = f.name
            try:
                result = subprocess.run(
                    [
                        binary,
                        "-m", self.model_path,
                        "-f", prompt_file,
                        "-n", "64",
                        "-t", "2",
                        "--ctx-size", "256",
                        "--temp", "0.3",
                        "--no-mmap",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=self.llama_dir,
                )
            finally:
                os.unlink(prompt_file)
            elapsed = time.time() - t0
            output = result.stdout.strip()
            if output:
                output = re.sub(r"<\|[^>]*\|>", "", output)
                output = re.sub(r"System:.*?Rewritten:", "", output, flags=re.DOTALL)
                lines = [l.strip() for l in output.split("\n") if l.strip()]
                output = "\n".join(lines)
                if output:
                    logger.info("AI rewrite done in %.1fs (len=%d)", elapsed, len(output))
                    return output
            logger.warning("AI returned empty output")
            return caption
        except subprocess.TimeoutExpired:
            logger.error("AI rewrite timed out after 120s")
            return caption
        except Exception as e:
            logger.error("AI rewrite failed: %s", e)
            return caption


ai_engine = AIEngine()
