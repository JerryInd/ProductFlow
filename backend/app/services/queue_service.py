import json
from app.database.connection import get_connection
from app.utils.logger import logger


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

    def _publish_item(self, item: dict):
        import asyncio
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

            loop = asyncio.new_event_loop()
            sent = True

            for path in media_paths:
                ok = loop.run_until_complete(whatsapp_service.send_media(dest_group, path, caption))
                if not ok:
                    logger.error(f"Failed to send media: {path}")
                    sent = False
                    break
                caption = ""

            if sent:
                for path in video_paths:
                    ok = loop.run_until_complete(whatsapp_service.send_media(dest_group, path, caption))
                    if not ok:
                        logger.error(f"Failed to send video: {path}")
                        sent = False
                        break
                    caption = ""

            loop.close()

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
                conn.execute(
                    "UPDATE queue SET status = 'failed', error = 'send failed', updated_at = datetime('now') WHERE id = ?",
                    (item["id"],),
                )
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
