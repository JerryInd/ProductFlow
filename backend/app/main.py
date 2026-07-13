import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import FRONTEND_URL
from app.database.connection import init_db
from app.utils.logger import logger
from app.api import home, whatsapp, groups, pipelines, products
from app.services.product_collector import product_collector
from app.services.pipeline_service import pipeline_service
from app.services.media_service import media_service

COLLECTOR_CHECK_INTERVAL = 15
MEDIA_CLEANUP_INTERVAL = 900  # 15 minutes

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
            await asyncio.to_thread(media_service.cleanup_orphans)
            await asyncio.to_thread(media_service.enforce_size_limit)
        except Exception:
            pass
        await asyncio.sleep(MEDIA_CLEANUP_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ProductFlow AI backend")
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning("Database init skipped: %s", e)
    collector_task = asyncio.create_task(collector_loop())
    cleanup_task = asyncio.create_task(media_cleanup_loop())
    yield
    collector_task.cancel()
    cleanup_task.cancel()
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

@app.get("/api/health")
def health():
    return {"status": "ok"}
