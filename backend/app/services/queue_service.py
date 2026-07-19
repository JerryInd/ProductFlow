import json
from app.database.connection import get_connection
from app.utils.logger import logger
from app.config import MAX_QUEUE_RETRIES

class QueueService:
    def enqueue(self, product_id: int, pipeline_id: int, destination_group_id: str):
        conn = get_connection()
        conn.execute(
            "INSERT INTO queue (product_id, pipeline_id, destination_group_id, status) VALUES (?, ?, ?, 'queued')",
            (product_id, pipeline_id, destination_group_id),
        )
        conn.commit()
        conn.close()
        logger.info(f"Queued product {product_id} -> {destination_group_id}")

    def enqueue_media(self, pipeline_id: int, destination_group_id: str, media_path: str, caption: str = "", media_type: str = "image"):
        conn = get_connection()
        conn.execute(
            "INSERT INTO relay_queue (pipeline_id, destination_group_id, relay_type, media_path, media_caption, status) VALUES (?, ?, ?, ?, ?, 'queued')",
            (pipeline_id, destination_group_id, media_type, media_path, caption),
        )
        conn.commit()
        conn.close()

    def enqueue_text(self, pipeline_id: int, destination_group_id: str, text: str):
        conn = get_connection()
        conn.execute(
            "INSERT INTO relay_queue (pipeline_id, destination_group_id, relay_type, relay_text, status) VALUES (?, ?, 'text', ?, 'queued')",
            (pipeline_id, destination_group_id, text),
        )
        conn.commit()
        conn.close()

    def process_queue(self, pipeline_id: int | None = None):
        conn = get_connection()
        query = "SELECT * FROM queue WHERE status = 'queued'"
        params = []
        if pipeline_id:
            query += " AND pipeline_id = ?"
            params.append(pipeline_id)
        query += " ORDER BY created_at ASC LIMIT 10"
        items = conn.execute(query, params).fetchall()
        conn.close()

        for item in items:
            self._publish_item(dict(item))

        self._process_relay_queue(pipeline_id)

    def _process_relay_queue(self, pipeline_id: int | None = None):
        conn = get_connection()
        query = "SELECT * FROM relay_queue WHERE status = 'queued'"
        params = []
        if pipeline_id:
            query += " AND pipeline_id = ?"
            params.append(pipeline_id)
        query += " ORDER BY created_at ASC LIMIT 20"
        items = conn.execute(query, params).fetchall()
        conn.close()

        for item in items:
            self._publish_relay_item(dict(item))

    def _publish_relay_item(self, item: dict):
        from app.services.whatsapp_service import whatsapp_service
        from app.services.media_service import media_service

        dest_group = item["destination_group_id"]
        relay_type = item["relay_type"]

        try:
            if relay_type in ("image", "video"):
                media_path = item.get("media_path", "")
                caption = item.get("media_caption", "")
                if not media_path:
                    conn = get_connection()
                    conn.execute("UPDATE relay_queue SET status = 'failed', error = 'no media path' WHERE id = ?", (item["id"],))
                    conn.commit()
                    conn.close()
                    return

                ok = whatsapp_service.send_media_sync(dest_group, media_path, caption)
                if ok:
                    conn = get_connection()
                    conn.execute("UPDATE relay_queue SET status = 'sent', updated_at = datetime('now') WHERE id = ?", (item["id"],))
                    conn.commit()
                    conn.close()
                    if media_path.startswith("media-cache/"):
                        media_service.delete(media_path)
                else:
                    self._fail_relay_item(item)

            elif relay_type == "text":
                text = item.get("relay_text", "")
                if not text:
                    conn = get_connection()
                    conn.execute("UPDATE relay_queue SET status = 'failed', error = 'empty text' WHERE id = ?", (item["id"],))
                    conn.commit()
                    conn.close()
                    return

                ok = whatsapp_service.send_message_sync(dest_group, text)
                if ok:
                    conn = get_connection()
                    conn.execute("UPDATE relay_queue SET status = 'sent', updated_at = datetime('now') WHERE id = ?", (item["id"],))
                    conn.commit()
                    conn.close()
                else:
                    self._fail_relay_item(item)
        except Exception as e:
            logger.error(f"Relay publish error: {e}")
            self._fail_relay_item(item)

    def _fail_relay_item(self, item: dict):
        new_count = item.get("retry_count", 0) + 1
        conn = get_connection()
        if new_count >= MAX_QUEUE_RETRIES:
            conn.execute(
                "UPDATE relay_queue SET status = 'dead', retry_count = ?, error = 'max retries', updated_at = datetime('now') WHERE id = ?",
                (new_count, item["id"]),
            )
            logger.error(f"Relay item {item['id']} dead after {new_count} retries")
        else:
            conn.execute(
                "UPDATE relay_queue SET status = 'failed', retry_count = ?, error = 'send failed', updated_at = datetime('now') WHERE id = ?",
                (new_count, item["id"]),
            )
        conn.commit()
        conn.close()

    def retry_failed(self):
        conn = get_connection()
        items = conn.execute(
            "SELECT * FROM queue WHERE status = 'failed' AND retry_count < ? ORDER BY created_at ASC LIMIT 5",
            (MAX_QUEUE_RETRIES,),
        ).fetchall()
        conn.close()

        if items:
            logger.info(f"Retrying {len(items)} failed queue items")
            for item in items:
                self._publish_item(dict(item))

        conn = get_connection()
        relay_items = conn.execute(
            "SELECT * FROM relay_queue WHERE status = 'failed' AND retry_count < ? ORDER BY created_at ASC LIMIT 10",
            (MAX_QUEUE_RETRIES,),
        ).fetchall()
        conn.close()

        if relay_items:
            logger.info(f"Retrying {len(relay_items)} failed relay items")
            for item in relay_items:
                self._publish_relay_item(dict(item))

    def _publish_item(self, item: dict):
        from app.services.whatsapp_service import whatsapp_service
        from app.services.media_service import media_service

        product_id = item["product_id"]
        dest_group = item["destination_group_id"]
        conn = get_connection()
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product:
            product = dict(product)
            media_paths = json.loads(product.get("media_paths") or "[]")
            video_paths = json.loads(product.get("video_paths") or "[]")
            caption = product.get("rewritten_caption") or product.get("caption") or ""

            logger.info(f"Publishing product {product_id} to {dest_group}: {len(media_paths)} images, {len(video_paths)} videos")

            sent = True

            for path in media_paths:
                ok = whatsapp_service.send_media_sync(dest_group, path, caption)
                if not ok:
                    logger.error(f"Failed to send media: {path}")
                    sent = False
                    break
                caption = ""

            if sent:
                for path in video_paths:
                    ok = whatsapp_service.send_media_sync(dest_group, path, caption)
                    if not ok:
                        logger.error(f"Failed to send video: {path}")
                        sent = False
                        break
                    caption = ""

            if sent:
                all_paths = media_paths + video_paths
                media_service.delete_many(all_paths)
                logger.info(f"Deleted {len(all_paths)} media files after publish")

                conn.execute(
                    "UPDATE queue SET status = 'published', updated_at = datetime('now') WHERE id = ?",
                    (item["id"],),
                )
                conn.execute(
                    "UPDATE products SET status = 'posted', media_paths = '[]', video_paths = '[]', updated_at = datetime('now') WHERE id = ?",
                    (product_id,),
                )
            else:
                new_count = item.get("retry_count", 0) + 1
                if new_count >= MAX_QUEUE_RETRIES:
                    conn.execute(
                        "UPDATE queue SET status = 'dead', retry_count = ?, error = 'max retries exceeded', updated_at = datetime('now') WHERE id = ?",
                        (new_count, item["id"]),
                    )
                    logger.error(f"Queue item {item['id']} moved to dead queue after {new_count} retries")
                else:
                    conn.execute(
                        "UPDATE queue SET status = 'failed', retry_count = ?, error = 'send failed', updated_at = datetime('now') WHERE id = ?",
                        (new_count, item["id"]),
                    )
                    logger.warning(f"Queue item {item['id']} failed (retry {new_count}/{MAX_QUEUE_RETRIES})")
        else:
            conn.execute(
                "UPDATE queue SET status = 'failed', error = 'product not found', updated_at = datetime('now') WHERE id = ?",
                (item["id"],),
            )
        conn.commit()
        conn.close()

    def get_pending_count(self) -> int:
        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM queue WHERE status = 'queued'").fetchone()[0]
        conn.close()
        return count

    def get_failed_count(self) -> int:
        conn = get_connection()
        count = conn.execute(
            "SELECT COUNT(*) FROM queue WHERE status = 'failed' AND retry_count < ?",
            (MAX_QUEUE_RETRIES,),
        ).fetchone()[0]
        conn.close()
        return count

    def get_all_pending(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT q.*, p.caption, p.rewritten_caption, p.media_paths, p.video_paths "
            "FROM queue q JOIN products p ON p.id = q.product_id "
            "WHERE q.status = 'queued' ORDER BY q.created_at ASC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


queue_service = QueueService()
