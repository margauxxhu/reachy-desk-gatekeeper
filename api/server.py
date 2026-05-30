"""FastAPI HTTP server — iMessage / home-network rail."""

import asyncio
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from core.gatekeeper import run_knock

log = logging.getLogger(__name__)

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8080


def build_server(robot, media, lock: asyncio.Lock) -> uvicorn.Server:
    app = FastAPI(title="Desk Gatekeeper")

    @app.post("/knock")
    async def knock():
        log.info("HTTP /knock received")
        result = await run_knock(robot, media, lock)
        return JSONResponse({
            "found":   result.found,
            "busy":    result.busy,
            "message": result.message,
        })

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    config = uvicorn.Config(
        app,
        host=HTTP_HOST,
        port=HTTP_PORT,
        log_level="warning",  # keep uvicorn quiet, our logger handles the rest
    )
    return uvicorn.Server(config)
