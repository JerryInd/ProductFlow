import os
from app.config import MODEL_PATH
from app.utils.logger import logger


class AIEngine:
    def __init__(self):
        self.model_path = MODEL_PATH
        self._model = None

    def is_available(self) -> bool:
        if not os.path.isfile(self.model_path):
            return False
        size = os.path.getsize(self.model_path)
        return size > 1024

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from ctransformers import AutoModelForCausalLM
            self._model = AutoModelForCausalLM.from_pretrained(
                os.path.dirname(self.model_path),
                model_type="llama",
                model_file=os.path.basename(self.model_path),
                max_new_tokens=192,
                temperature=0.7,
            )
            logger.info("Loaded model from %s", self.model_path)
            return self._model
        except Exception as e:
            logger.error("Failed to load model: %s", e)
            return None

    def rewrite(self, caption, prompt_template, new_price=None):
        if not self.is_available():
            logger.warning("Model not found at %s", self.model_path)
            return caption
        try:
            model = self._load_model()
            if not model:
                return caption
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
                user_input += f"\n\nNew Price: Rs.{new_price}"
            prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_input}\n<|assistant|>\n"
            import time
            t0 = time.time()
            output = model(prompt, max_new_tokens=192, temperature=0.7)
            elapsed = time.time() - t0
            result = output if isinstance(output, str) else str(output)
            if result:
                logger.info("AI rewrite done in %.1fs (len=%d)", elapsed, len(result))
                return result.strip()
            return caption
        except Exception as e:
            logger.error("AI rewrite failed: %s", e)
            return caption


ai_engine = AIEngine()
