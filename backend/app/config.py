import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "database" / "productflow.db"))
MEDIA_CACHE_DIR = os.getenv("MEDIA_CACHE_DIR", str(BASE_DIR / "media-cache"))
SESSIONS_DIR = os.getenv("SESSIONS_DIR", str(BASE_DIR / "sessions"))
MODELS_DIR = os.getenv("MODELS_DIR", str(BASE_DIR / "models"))
PROMPTS_DIR = os.getenv("PROMPTS_DIR", str(BASE_DIR / "prompts"))
PIPELINES_DIR = os.getenv("PIPELINES_DIR", str(BASE_DIR / "pipelines"))
LOGS_DIR = os.getenv("LOGS_DIR", str(BASE_DIR / "logs"))
BACKUPS_DIR = os.getenv("BACKUPS_DIR", str(BASE_DIR / "backups"))

MODEL_FILENAME = os.getenv("MODEL_FILENAME", "smollm2-135m.gguf")
MODEL_PATH = os.path.join(MODELS_DIR, MODEL_FILENAME)
LLAMA_CPP_PATH = os.getenv("LLAMA_CPP_PATH", "llama-cli")

WHATSAPP_SESSION_NAME = os.getenv("WHATSAPP_SESSION_NAME", "productflow-session")

MEDIA_MAX_CACHE_GB = int(os.getenv("MEDIA_MAX_CACHE_GB", "5"))
MEDIA_RETENTION_HOURS = int(os.getenv("MEDIA_RETENTION_HOURS", "24"))

COLLECTOR_WINDOW_SECONDS = int(os.getenv("COLLECTOR_WINDOW_SECONDS", "90"))
COLLECTOR_MAX_IDLE_SECONDS = int(os.getenv("COLLECTOR_MAX_IDLE_SECONDS", "300"))
COLLECTOR_MAX_MEDIA = int(os.getenv("COLLECTOR_MAX_MEDIA", "20"))

MAX_RAM_MB = int(os.getenv("MAX_RAM_MB", "450"))
SWAP_MB = int(os.getenv("SWAP_MB", "1024"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_MAX_MB = int(os.getenv("LOG_MAX_MB", "5"))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "2"))

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://productflow.pages.dev")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "1"))
