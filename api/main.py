"""
CSIS SmartAssist — FastAPI Application Bootstrap

Clean entry point that registers middleware, CORS, and all API routes.
Designed for deployment on Render's free tier.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from routes import booking, chat, rag

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Application ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="CSIS SmartAssist API",
    description=(
        "AI-powered departmental assistant for the CSIS Department, "
        "BITS Pilani, K K Birla Goa Campus."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ─────────────────────────────────────────────────────────

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router Registration ────────────────────────────────────────────────────

app.include_router(chat.router, prefix="/api")
app.include_router(booking.router, prefix="/api")
app.include_router(rag.router, prefix="/api")


# ── Health Check ────────────────────────────────────────────────────────────


@app.get("/health")
@app.head("/health")
async def health_check():
    """Lightweight health probe for uptime monitoring."""
    return {"status": "healthy", "service": "csis-smartassist-api"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "CSIS SmartAssist API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


logger.info("CSIS SmartAssist API initialized successfully.")
