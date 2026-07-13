import os
import shutil
import time
from pathlib import Path
from app.config import MEDIA_CACHE_DIR, MEDIA_MAX_CACHE_GB, MEDIA_RETENTION_HOURS
from app.utils.logger import logger

class MediaService:
    def __init__(self):
        self.cache_dir = Path(MEDIA_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def store(self, data: bytes, filename: str) -> str:
        dest = self.cache_dir / filename
        dest.write_bytes(data)
        return str(dest)

    def get_path(self, filename: str) -> str | None:
        path = self.cache_dir / filename
        return str(path) if path.exists() else None

    def cleanup(self):
        cutoff = time.time() - (MEDIA_RETENTION_HOURS * 3600)
        removed = 0
        for f in self.cache_dir.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        if removed:
            logger.info(f"Cleaned up {removed} expired media files")

    def delete(self, filepath: str) -> bool:
        path = Path(filepath)
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False

    def delete_many(self, paths: list[str]) -> int:
        removed = 0
        for p in paths:
            if self.delete(p):
                removed += 1
        return removed

    def enforce_size_limit(self):
        total = sum(f.stat().st_size for f in self.cache_dir.iterdir() if f.is_file())
        limit_bytes = MEDIA_MAX_CACHE_GB * 1024**3
        if total > limit_bytes:
            files = sorted(
                [f for f in self.cache_dir.iterdir() if f.is_file()],
                key=lambda f: f.stat().st_mtime,
            )
            while total > limit_bytes and files:
                f = files.pop(0)
                total -= f.stat().st_size
                f.unlink()
            logger.info(f"Media cache trimmed to under {MEDIA_MAX_CACHE_GB}GB")

media_service = MediaService()
