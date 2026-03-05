"""Forge API — FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from .routes import router

app = FastAPI(title="Forge Orchestrator", version="0.1.0")
app.include_router(router, prefix="/api")
