import os
import json
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

    def cleanup_orphans(self):
        from app.database.connection import get_connection
        disk_files = {f.name for f in self.cache_dir.iterdir() if f.is_file()}
        if not disk_files:
            return

        referenced = set()
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT media_paths, video_paths FROM products WHERE status != 'posted'"
            ).fetchall()
            for row in rows:
                referenced.update(json.loads(row["media_paths"] or "[]"))
                referenced.update(json.loads(row["video_paths"] or "[]"))

            from app.services.product_collector import product_collector
            for coll in product_collector.active_collections.values():
                referenced.update(coll.get("media_paths", []))
                referenced.update(coll.get("video_paths", []))
        finally:
            conn.close()

        referenced_names = {Path(p).name for p in referenced}
        orphans = disk_files - referenced_names
        removed = 0
        for name in orphans:
            f = self.cache_dir / name
            if f.is_file():
                f.unlink()
                removed += 1
        if removed:
            logger.info(f"Cleaned up {removed} orphaned media files")

media_service = MediaService()
