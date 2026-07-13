from app.database.connection import get_connection
from app.utils.logger import logger
from app.services.queue_service import queue_service

class RecoveryService:
    def recover(self):
        logger.info("Starting recovery sequence")
        self._restore_whatsapp_session()
        self._load_pipelines()
        self._process_queue()
        self._recover_missed_products()
        logger.info("Recovery complete")

    def _restore_whatsapp_session(self):
        conn = get_connection()
        session = conn.execute(
            "SELECT * FROM whatsapp_sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if session and session["status"] == "connected":
            logger.info(f"Found saved session: {session['session_name']}")
        else:
            logger.info("No saved session found, waiting for QR login")

    def _load_pipelines(self):
        conn = get_connection()
        pipelines = conn.execute(
            "SELECT id, name, enabled FROM pipelines WHERE enabled = 1"
        ).fetchall()
        conn.close()
        logger.info(f"Loaded {len(pipelines)} enabled pipelines")
        for p in pipelines:
            logger.info(f"  Pipeline: {p['name']} (id={p['id']})")

    def _process_queue(self):
        pending = queue_service.get_pending_count()
        logger.info(f"Pending queue items: {pending}")
        if pending > 0:
            queue_service.process_queue()

    def _recover_missed_products(self):
        conn = get_connection()
        pipelines = conn.execute("SELECT id, name FROM pipelines WHERE enabled = 1").fetchall()
        for p in pipelines:
            last_msg = conn.execute(
                "SELECT message_id, group_id FROM processed_messages WHERE pipeline_id = ? ORDER BY processed_at DESC LIMIT 1",
                (p["id"],),
            ).fetchone()
            if last_msg:
                logger.info(f"Pipeline '{p['name']}': last processed msg {last_msg['message_id']}")
            else:
                logger.info(f"Pipeline '{p['name']}': no previous messages")
        conn.close()

recovery_service = RecoveryService()
