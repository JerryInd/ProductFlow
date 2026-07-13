from app.database.connection import get_connection
from app.utils.helpers import compute_product_hash

class DuplicateDetector:
    @staticmethod
    def is_duplicate(caption: str, media_count: int, source_group_id: str) -> bool:
        h = compute_product_hash(caption, media_count, source_group_id)
        conn = get_connection()
        row = conn.execute("SELECT id FROM products WHERE hash = ?", (h,)).fetchone()
        conn.close()
        return row is not None

    @staticmethod
    def is_message_processed(message_id: str, group_id: str) -> bool:
        conn = get_connection()
        row = conn.execute(
            "SELECT id FROM processed_messages WHERE message_id = ? AND group_id = ?",
            (message_id, group_id),
        ).fetchone()
        conn.close()
        return row is not None

    @staticmethod
    def mark_processed(message_id: str, group_id: str, pipeline_id: int | None = None):
        conn = get_connection()
        conn.execute(
            "INSERT OR IGNORE INTO processed_messages (message_id, group_id, pipeline_id) VALUES (?, ?, ?)",
            (message_id, group_id, pipeline_id),
        )
        conn.commit()
        conn.close()

duplicate_detector = DuplicateDetector()
