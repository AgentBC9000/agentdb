import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.db.client import connect_db, disconnect_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    print(f"🚀 AgentDB API starting — env: {settings.ENVIRONMENT}")
    yield
    await disconnect_db()
    print("AgentDB API shutting down")


app = FastAPI(
    title="AgentDB",
    description="Real-time curated knowledge API for AI agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/v1")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import sys
    print(
        f"ERROR {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}",
        file=sys.stderr,
        flush=True,
    )
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/debug/db")
async def debug_db():
    """Temporary: reveal which DB the app is connected to."""
    import re
    def mask(url):
        return re.sub(r":([^@]+)@", ":***@", url) if url else "(empty)"
    return {
        "AGENTDB_DATABASE_URL": mask(settings.AGENTDB_DATABASE_URL),
        "DATABASE_URL": mask(settings.DATABASE_URL),
        "using": mask(settings.AGENTDB_DATABASE_URL or settings.DATABASE_URL),
    }


@app.get("/debug/auth")
async def debug_auth():
    """Temporary: show masked admin secret so we can confirm which value Railway is serving."""
    import os
    from app.core.config import get_admin_secret
    resolved = get_admin_secret()
    def mask(v):
        return v[:4] + "***" if v and len(v) > 4 else "(empty or short)"
    return {
        "ADMIN_SECRET_raw": mask(os.environ.get("ADMIN_SECRET", "")),
        "AGENTDB_ADMIN_SECRET_raw": mask(os.environ.get("AGENTDB_ADMIN_SECRET", "")),
        "resolved": mask(resolved),
    }
