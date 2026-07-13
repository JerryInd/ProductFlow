import json
import time
from app.database.connection import get_connection
from app.utils.logger import logger
from app.config import COLLECTOR_MAX_IDLE_SECONDS, COLLECTOR_MAX_MEDIA

class ProductCollector:
    def __init__(self):
        self.active_collections: dict[str, dict] = {}
        self.max_idle = max(COLLECTOR_MAX_IDLE_SECONDS, 120)
        self.max_media = max(COLLECTOR_MAX_MEDIA, 5)

    def start_collection(self, pipeline_id: int, source_group_id: str, window_seconds: int = 40):
        key = f"{pipeline_id}:{source_group_id}"
        if key in self.active_collections:
            return
        window = max(window_seconds, 15)
        now = time.time()
        self.active_collections[key] = {
            "pipeline_id": pipeline_id,
            "source_group_id": source_group_id,
            "media_paths": [],
            "video_paths": [],
            "message_ids": [],
            "caption": "",
            "started_at": now,
            "last_msg_at": now,
            "window_seconds": window,
        }
        self._save_to_db(pipeline_id, source_group_id)
        logger.info("Collection started: pipeline %s group %s window %ss", pipeline_id, source_group_id, window)

    def add_media(self, pipeline_id: int, source_group_id: str, media_path: str, is_video: bool = False):
        key = f"{pipeline_id}:{source_group_id}"
        coll = self.active_collections.get(key)
        if not coll:
            return
        media_list = coll["video_paths"] if is_video else coll["media_paths"]
        if len(media_list) >= self.max_media:
            logger.warning("Max media (%d) reached for %s:%s", self.max_media, pipeline_id, source_group_id)
            return
        media_list.append(media_path)
        coll["last_msg_at"] = time.time()
        self._save_to_db(pipeline_id, source_group_id)

    def add_message_id(self, pipeline_id: int, source_group_id: str, msg_id: str):
        key = f"{pipeline_id}:{source_group_id}"
        coll = self.active_collections.get(key)
        if coll:
            coll["last_msg_at"] = time.time()
            coll["message_ids"].append(msg_id)
            self._save_to_db(pipeline_id, source_group_id)

    def update_caption(self, pipeline_id: int, source_group_id: str, caption: str):
        key = f"{pipeline_id}:{source_group_id}"
        coll = self.active_collections.get(key)
        if coll:
            coll["last_msg_at"] = time.time()
            parts = [coll["caption"], caption]
            coll["caption"] = "\n".join(p for p in parts if p).strip()
            self._save_to_db(pipeline_id, source_group_id)

    def finalize(self, pipeline_id: int, source_group_id: str, coll: dict | None = None) -> dict | None:
        key = f"{pipeline_id}:{source_group_id}"
        if coll is None:
            coll = self.active_collections.pop(key, None)
        else:
            self.active_collections.pop(key, None)
        self._delete_from_db(pipeline_id, source_group_id)
        if not coll:
            return None
        if not coll["media_paths"] and not coll["video_paths"] and not coll["caption"]:
            return None
        return coll

    def check_expired(self) -> list[dict]:
        now = time.time()
        expired = []
        keys = list(self.active_collections.keys())
        for key in keys:
            coll = self.active_collections.get(key)
            if not coll:
                continue
            since_last = now - coll["last_msg_at"]
            since_start = now - coll["started_at"]
            timed_out = since_last >= coll["window_seconds"]
            idle_too_long = since_start >= self.max_idle
            if timed_out or idle_too_long:
                self.active_collections.pop(key, None)
                self._delete_from_db(coll["pipeline_id"], coll["source_group_id"])
                if coll["media_paths"] or coll["video_paths"] or coll["caption"]:
                    expired.append(coll)
                    logger.info(
                        "Collection expired: pipeline %s group %s (%.0fs idle, %.0fs total)",
                        coll["pipeline_id"], coll["source_group_id"],
                        since_last, since_start,
                    )
        return expired

    def load_from_db(self):
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM active_collections").fetchall()
            for row in rows:
                r = dict(row)
                key = f"{r['pipeline_id']}:{r['source_group_id']}"
                self.active_collections[key] = {
                    "pipeline_id": r["pipeline_id"],
                    "source_group_id": r["source_group_id"],
                    "media_paths": json.loads(r["media_paths"]),
                    "video_paths": json.loads(r["video_paths"]),
                    "message_ids": json.loads(r["message_ids"]),
                    "caption": r["caption"],
                    "started_at": r["started_at"],
                    "last_msg_at": r["last_msg_at"],
                    "window_seconds": r["window_seconds"],
                }
                logger.info(
                    "Loaded active collection: pipeline %s group %s (%d media, %d videos)",
                    r["pipeline_id"], r["source_group_id"],
                    len(self.active_collections[key]["media_paths"]),
                    len(self.active_collections[key]["video_paths"]),
                )
            if rows:
                logger.info("Loaded %d active collections from database", len(rows))
        finally:
            conn.close()

    def _save_to_db(self, pipeline_id: int, source_group_id: str):
        key = f"{pipeline_id}:{source_group_id}"
        coll = self.active_collections.get(key)
        if not coll:
            return
        conn = get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO active_collections
                   (pipeline_id, source_group_id, media_paths, video_paths,
                    message_ids, caption, started_at, last_msg_at, window_seconds)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pipeline_id, source_group_id,
                    json.dumps(coll["media_paths"]),
                    json.dumps(coll["video_paths"]),
                    json.dumps(coll["message_ids"]),
                    coll["caption"],
                    coll["started_at"],
                    coll["last_msg_at"],
                    coll["window_seconds"],
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _delete_from_db(self, pipeline_id: int, source_group_id: str):
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM active_collections WHERE pipeline_id = ? AND source_group_id = ?",
                (pipeline_id, source_group_id),
            )
            conn.commit()
        finally:
            conn.close()

    def save_product(self, collection: dict, rewritten_caption: str, price_original: int | None, price_new: int | None) -> int | None:
        conn = get_connection()
        try:
            media_json = json.dumps(collection["media_paths"])
            video_json = json.dumps(collection["video_paths"])
            msg_json = json.dumps(collection["message_ids"])
            cur = conn.execute(
                """INSERT INTO products
                   (pipeline_id, source_group_id, caption, rewritten_caption,
                    media_paths, video_paths, message_ids,
                    price_original, price_new, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'collected')""",
                (collection["pipeline_id"], collection["source_group_id"],
                 collection["caption"], rewritten_caption,
                 media_json, video_json, msg_json,
                 price_original, price_new),
            )
            conn.commit()
            pid = cur.lastrowid
            logger.info("Product saved id=%d", pid)
            return pid
        finally:
            conn.close()

product_collector = ProductCollector()
