import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import FRONTEND_URL
from app.database.connection import init_db
from app.utils.logger import logger
from app.api import home, whatsapp, groups, pipelines, products, forward, relay
from app.services.product_collector import product_collector
from app.services.pipeline_service import pipeline_service
from app.services.media_service import media_service
from app.services.queue_service import queue_service
from app.services.recovery_service import recovery_service

COLLECTOR_CHECK_INTERVAL = 15
MEDIA_CLEANUP_INTERVAL = 300  # 5 minutes
QUEUE_RETRY_INTERVAL = 60  # 1 minute

async def collector_loop():
    while True:
        try:
            expired = product_collector.check_expired()
            for coll in expired:
                pid = coll.get("pipeline_id")
                gid = coll.get("source_group_id")
                if pid and gid:
                    await asyncio.to_thread(pipeline_service.finalize_collection, pid, gid, coll)
        except Exception as e:
            logger.error("Collector loop error: %s", e)
        await asyncio.sleep(COLLECTOR_CHECK_INTERVAL)

async def media_cleanup_loop():
    while True:
        try:
            await asyncio.to_thread(media_service.cleanup)
            await asyncio.to_thread(media_service.enforce_size_limit)
        except Exception:
            pass
        await asyncio.sleep(MEDIA_CLEANUP_INTERVAL)

async def queue_retry_loop():
    while True:
        try:
            await asyncio.to_thread(queue_service.retry_failed)
        except Exception as e:
            logger.error("Queue retry loop error: %s", e)
        await asyncio.sleep(QUEUE_RETRY_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ProductFlow AI backend")
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning("Database init skipped: %s", e)
    try:
        await asyncio.to_thread(recovery_service.recover)
    except Exception as e:
        logger.warning("Recovery failed: %s", e)
    collector_task = asyncio.create_task(collector_loop())
    cleanup_task = asyncio.create_task(media_cleanup_loop())
    retry_task = asyncio.create_task(queue_retry_loop())
    yield
    collector_task.cancel()
    cleanup_task.cancel()
    retry_task.cancel()
    logger.info("Shutting down ProductFlow AI backend")

app = FastAPI(title="ProductFlow AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home.router, prefix="/api/home", tags=["Home"])
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["WhatsApp"])
app.include_router(groups.router, prefix="/api/groups", tags=["Groups"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["Pipelines"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(forward.router, prefix="/api", tags=["Forward"])
app.include_router(relay.router, prefix="/api/relay", tags=["Relay"])

@app.get("/api/health")
def health():
    return {"status": "ok"}

FRONTEND_BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "build")

if os.path.isdir(FRONTEND_BUILD):
    app.mount("/_app", StaticFiles(directory=os.path.join(FRONTEND_BUILD, "_app")), name="static")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = os.path.join(FRONTEND_BUILD, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_BUILD, "index.html"))
