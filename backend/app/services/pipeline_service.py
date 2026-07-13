from app.database.connection import get_connection
from app.services.ai_engine import ai_engine
from app.services.pricing_engine import pricing_engine
from app.services.product_collector import product_collector
from app.services.duplicate_detector import duplicate_detector
from app.services.queue_service import queue_service
from app.utils.helpers import replace_price, serialize_row
from app.utils.logger import logger

class PipelineService:
    def process_message(self, pipeline_id: int, source_group_id: str, message: dict):
        msg_id = message.get("id", "")
        if not msg_id:
            return
        if duplicate_detector.is_message_processed(msg_id, source_group_id):
            return

        pipeline = self._get_pipeline(pipeline_id)
        if not pipeline or not pipeline["enabled"]:
            return

        collector_window = pipeline.get("collector_window_seconds") or 40
        msg_type = message.get("type", "")
        logger.info("Msg type=%s text=%d media_path=%d", msg_type, len(message.get("text", "")), len(message.get("media_path", "")))

        key = f"{pipeline_id}:{source_group_id}"
        existing = product_collector.active_collections.get(key)

        if msg_type == "text" or msg_type == "caption":
            if existing and existing.get("media_paths"):
                logger.info("Text separator: finalizing current collection before new caption")
                product_collector.finalize(pipeline_id, source_group_id)
                queue_service.process_queue(pipeline_id)
                existing = None

            product_collector.start_collection(pipeline_id, source_group_id, collector_window)
            product_collector.update_caption(pipeline_id, source_group_id, message.get("text", ""))

        elif msg_type == "image":
            product_collector.start_collection(pipeline_id, source_group_id, collector_window)
            product_collector.add_media(pipeline_id, source_group_id, message.get("media_path", ""))
            if message.get("text"):
                product_collector.update_caption(pipeline_id, source_group_id, message["text"])

        elif msg_type == "video":
            product_collector.start_collection(pipeline_id, source_group_id, collector_window)
            product_collector.add_media(pipeline_id, source_group_id, message.get("media_path", ""), is_video=True)
            if message.get("text"):
                product_collector.update_caption(pipeline_id, source_group_id, message["text"])

        else:
            product_collector.start_collection(pipeline_id, source_group_id, collector_window)

        product_collector.add_message_id(pipeline_id, source_group_id, msg_id)
        duplicate_detector.mark_processed(msg_id, source_group_id, pipeline_id)

    def finalize_collection(self, pipeline_id: int, source_group_id: str, collection: dict | None = None):
        col = product_collector.finalize(pipeline_id, source_group_id, collection)
        if not col:
            logger.warning("Finalize: empty collection for pipeline %s group %s", pipeline_id, source_group_id)
            return

        logger.info("Finalize: media=%d video=%d caption=%d chars",
                     len(col["media_paths"]), len(col["video_paths"]),
                     len(col["caption"]))

        pipeline = self._get_pipeline(pipeline_id)
        if not pipeline:
            logger.warning("Finalize: pipeline %s not found", pipeline_id)
            return

        caption = col["caption"]
        mode = pipeline.get("pricing_mode", "percentage")
        value = pipeline.get("pricing_value", 0)
        tiers = pipeline.get("pricing_tiers")

        _, orig_price, new_price = pricing_engine.process_caption(caption, mode, value, tiers)
        updated_caption = caption
        if orig_price and new_price:
            updated_caption = replace_price(caption, orig_price, new_price)

        prompt = pipeline.get("prompt_template", "")
        rewritten = ai_engine.rewrite(updated_caption, prompt, new_price)

        product_id = product_collector.save_product(col, rewritten, orig_price, new_price)
        if not product_id:
            logger.error("Finalize: failed to save product for pipeline %s", pipeline_id)
            return

        logger.info("Finalize: product %d saved", product_id)

        destinations = self._get_destinations(pipeline_id)
        for dest in destinations:
            gid = dest.get("group_id", "")
            if gid:
                queue_service.enqueue(product_id, pipeline_id, gid)

        if pipeline.get("auto_publish"):
            queue_service.process_queue(pipeline_id)
            logger.info("Pipeline %s: auto-published product %s", pipeline_id, product_id)

    def _get_pipeline(self, pipeline_id: int) -> dict | None:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)).fetchone()
            return serialize_row(row) if row else None
        finally:
            conn.close()

    def _get_destinations(self, pipeline_id: int) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT group_id FROM pipeline_destinations WHERE pipeline_id = ?",
                (pipeline_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_all_enabled(self) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM pipelines WHERE enabled = 1").fetchall()
            result = []
            for r in rows:
                p = serialize_row(r)
                sources = conn.execute(
                    "SELECT group_id FROM pipeline_sources WHERE pipeline_id = ?", (r["id"],)
                ).fetchall()
                p["sources"] = [dict(s) for s in sources]
                result.append(p)
            return result
        finally:
            conn.close()

pipeline_service = PipelineService()
