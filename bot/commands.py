"""Discord slash command definitions for the Desk Gatekeeper bot."""

import asyncio
import logging
from typing import Optional, Tuple

import discord
from discord import app_commands

from vision.face_detection import capture_and_detect, DetectionResult
from vision.gesture import detect_nods
from robot.movements import search_for_face, hold_gaze, react_busy, react_available

log = logging.getLogger(__name__)

NOD_WINDOW_SECONDS = 8


def _largest_face_center(result: DetectionResult) -> Optional[Tuple[int, int]]:
    """Return pixel (u, v) of the largest face, clamped to image bounds."""
    if not result.boxes or result.frame is None:
        return None
    h_img, w_img = result.frame.shape[:2]
    x, y, w, h = max(result.boxes, key=lambda b: b[2] * b[3])
    u = max(1, min(int(x + w / 2), w_img - 1))
    v = max(1, min(int(y + h / 2), h_img - 1))
    return (u, v)


def register_commands(tree: app_commands.CommandTree, robot, media) -> None:
    """Attach all slash commands to *tree*. Call once at bot startup."""

    @tree.command(
        name="knock",
        description="Ask if it's okay to come in — Reachy will check and report back.",
    )
    async def knock(interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        loop = asyncio.get_event_loop()

        # ── Step 1: search for the user's face ───────────────────────────────
        await interaction.edit_original_response(
            content="Searching for the user... 👀"
        )

        if robot is not None:
            face_result = await loop.run_in_executor(
                None, search_for_face, robot, media
            )
        else:
            # Robot not connected — fall back to single capture
            try:
                face_result = await loop.run_in_executor(
                    None, capture_and_detect, media
                )
                if not face_result.face_detected:
                    face_result = None
            except RuntimeError:
                face_result = None

        if face_result is None:
            await interaction.edit_original_response(
                content="Could not find the user. They may be away from their desk."
            )
            return

        # ── Step 2: lock gaze, wait for nod ──────────────────────────────────
        face_center = _largest_face_center(face_result)

        if robot is not None and face_center is not None:
            await loop.run_in_executor(None, hold_gaze, robot, face_center)

        await interaction.edit_original_response(
            content=(
                f"Found them! Waiting for their response "
                f"({NOD_WINDOW_SECONDS}s)... 🤔"
            )
        )

        busy = await loop.run_in_executor(
            None, detect_nods, media, float(NOD_WINDOW_SECONDS)
        )

        # ── Step 3: robot reacts, Discord reports ─────────────────────────────
        if robot is not None:
            await loop.run_in_executor(
                None, react_busy if busy else react_available, robot
            )

        if busy:
            embed = discord.Embed(
                title="🔴  Do Not Disturb",
                description="They nodded twice — they're in a call. Please wait.",
                color=discord.Color.red(),
            )
        else:
            embed = discord.Embed(
                title="🟢  Come On In",
                description="No signal — they're available. Go ahead!",
                color=discord.Color.green(),
            )

        embed.set_footer(text="Reachy Mini · Desk Gatekeeper")
        await interaction.edit_original_response(content=None, embed=embed)
