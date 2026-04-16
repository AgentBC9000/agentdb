from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.api.v1 import router as api_v1_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 AgentDB API starting — env: {settings.ENVIRONMENT}")
    yield
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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
