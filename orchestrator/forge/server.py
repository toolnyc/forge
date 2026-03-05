"""Forge server — runs FastAPI, Telegram bot, and background worker together."""

from __future__ import annotations

import asyncio
import logging

import uvicorn

from .config import config

log = logging.getLogger("forge.server")


async def _run_api() -> None:
    """Run FastAPI via uvicorn."""
    from .api import app

    server_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.port,
        log_level="info",
    )
    server = uvicorn.Server(server_config)
    await server.serve()


async def _run_telegram() -> None:
    """Run Telegram bot if token is configured."""
    if not config.telegram_bot_token:
        log.info("TELEGRAM_BOT_TOKEN not set, skipping Telegram bot")
        return
    from .telegram import start_bot
    await start_bot()


async def _run_worker() -> None:
    """Run the background task worker."""
    from .worker import run_worker
    await run_worker()


async def start() -> None:
    """Start all services concurrently."""
    log.info("Starting Forge server on port %d", config.port)

    tasks = [
        asyncio.create_task(_run_api(), name="api"),
        asyncio.create_task(_run_worker(), name="worker"),
    ]

    if config.telegram_bot_token:
        tasks.append(asyncio.create_task(_run_telegram(), name="telegram"))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        log.info("Forge server shutting down")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
