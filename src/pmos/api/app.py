import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..config import get_settings
from ..streaming.manager import get_stream_manager
from .deps import build_ingestor, get_prediction_service
from .routes import batch, health, meta, stream

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    svc = get_prediction_service()

    mgr = get_stream_manager()
    try:
        ingestor = build_ingestor()
        mgr.configure(
            ingestor,
            svc,
            rpm=settings.default_rpm,
            triplet_max_age_s=settings.triplet_max_age_s,
        )
        await mgr.start()
    except Exception:
        logging.getLogger(__name__).exception(
            "failed to start ingestor; WS will accept clients but emit no predictions"
        )

    try:
        yield
    finally:
        await mgr.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(title="Maintenance_OS", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(meta.router)
    app.include_router(batch.router)
    app.include_router(stream.router)

    if _FRONTEND_DIR.exists():
        app.mount(
            "/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend"
        )

    return app


app = create_app()
