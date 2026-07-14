import json
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

        destinations = self._get_destinations(pipeline_id)
        if not destinations:
            logger.warning("No destinations for pipeline %s", pipeline_id)
            return

        if msg_type in ("image", "video") and message.get("media_path"):
            caption = message.get("text", "")
            for dest in destinations:
                gid = dest.get("group_id", "")
                if gid:
                    queue_service.enqueue_media(pipeline_id, gid, message["media_path"], caption, msg_type)
            if pipeline.get("auto_publish"):
                queue_service.process_queue(pipeline_id)

        elif msg_type == "text" or msg_type == "caption":
            text = message.get("text", "")
            if not text:
                return
            caption, orig_price, new_price = pricing_engine.process_caption(
                text, pipeline.get("pricing_mode", "percentage"),
                pipeline.get("pricing_value", 0), pipeline.get("pricing_tiers")
            )
            updated_text = text
            if orig_price and new_price:
                updated_text = replace_price(text, orig_price, new_price)

            prompt = pipeline.get("prompt_template", "")
            rewritten = ai_engine.rewrite(updated_text, prompt, new_price)

            for dest in destinations:
                gid = dest.get("group_id", "")
                if gid:
                    queue_service.enqueue_text(pipeline_id, gid, rewritten)
            if pipeline.get("auto_publish"):
                queue_service.process_queue(pipeline_id)

        product_collector.add_message_id(pipeline_id, source_group_id, msg_id)
        duplicate_detector.mark_processed(msg_id, source_group_id, pipeline_id)

    def finalize_collection(self, pipeline_id: int, source_group_id: str, collection: dict | None = None):
        col = product_collector.finalize(pipeline_id, source_group_id, collection)
        if not col:
            return

        if not col["media_paths"] and not col["video_paths"]:
            return

        logger.info("Finalize: media=%d video=%d caption=%d chars",
                     len(col["media_paths"]), len(col["video_paths"]),
                     len(col["caption"]))

        pipeline = self._get_pipeline(pipeline_id)
        if not pipeline:
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
            return

        logger.info("Finalize: product %d saved", product_id)

        destinations = self._get_destinations(pipeline_id)
        for dest in destinations:
            gid = dest.get("group_id", "")
            if gid:
                queue_service.enqueue(product_id, pipeline_id, gid)

        if pipeline.get("auto_publish"):
            queue_service.process_queue(pipeline_id)

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
