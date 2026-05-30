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
from vision.face_detection import init_media

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def _connect_robot():
    """Return a live ReachyMini connection, or None if unavailable."""
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
    def __init__(self, robot, media) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.robot = robot
        self.media = media
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        register_commands(self.tree, self.robot, self.media)

        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Slash commands synced to guild %s", guild_id)
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally (may take up to 1 hour to propagate)")

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

    # Reuse the MediaManager already created by ReachyMini to avoid two
    # GStreamer pipelines competing for the same IPC camera endpoint.
    if robot is not None:
        media = robot.media
        log.info("Using Reachy's onboard camera via robot.media")
    else:
        media = init_media()
        log.info("No robot connection — initializing standalone camera pipeline")

    async with GatekeeperBot(robot, media) as bot:
        try:
            await bot.start(token)
        finally:
            if robot is None:
                media.close()


if __name__ == "__main__":
    asyncio.run(main())
