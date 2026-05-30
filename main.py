"""Desk Gatekeeper — entry point.

Usage:
    source /venvs/apps_venv/bin/activate
    python main.py
"""

import asyncio
import logging
import os
from typing import Optional

import discord
from discord import app_commands
from dotenv import load_dotenv

from bot.commands import register_commands
from api.server import build_server
from vision.face_detection import init_media

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def _connect_robot():
    host = os.getenv("REACHY_HOST", "localhost")
    port = int(os.getenv("REACHY_PORT", "8000"))
    try:
        from reachy_mini import ReachyMini
        robot = ReachyMini(host=host, port=port)
        log.info("Connected to Reachy Mini at %s:%s", host, port)
        return robot
    except Exception as exc:
        log.warning("Reachy Mini not available (%s) — running in camera-only mode", exc)
        return None


class GatekeeperBot(discord.Client):
    def __init__(self, robot, media, lock: asyncio.Lock) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.robot = robot
        self.media = media
        self.lock = lock
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        register_commands(self.tree, self.robot, self.media, self.lock)

        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Slash commands synced to guild %s", guild_id)
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="the desk 👀",
            )
        )


async def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN not set — copy .env.example to .env and fill it in.")

    robot = _connect_robot()
    media = robot.media if robot is not None else init_media()
    lock = asyncio.Lock()

    if robot is not None:
        log.info("Using Reachy's onboard camera via robot.media")
    else:
        log.info("No robot — initializing standalone camera pipeline")

    http_server = build_server(robot, media, lock)
    log.info("HTTP server will listen on 0.0.0.0:8080")

    bot = GatekeeperBot(robot, media, lock)

    async with bot:
        await asyncio.gather(
            bot.start(token),
            http_server.serve(),
        )


if __name__ == "__main__":
    asyncio.run(main())
