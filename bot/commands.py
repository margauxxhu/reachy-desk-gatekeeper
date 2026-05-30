"""Discord slash command definitions for the Desk Gatekeeper bot."""

import asyncio
import logging

import discord
from discord import app_commands

from core.gatekeeper import run_knock

log = logging.getLogger(__name__)


def register_commands(tree: app_commands.CommandTree, robot, media, lock: asyncio.Lock) -> None:
    """Attach all slash commands to *tree*. Call once at bot startup."""

    @tree.command(
        name="knock",
        description="Ask if it's okay to come in — Reachy will check and report back.",
    )
    async def knock(interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.edit_original_response(content="Searching for the user... 👀")

        result = await run_knock(robot, media, lock)

        if not result.found:
            await interaction.edit_original_response(content=result.message)
            return

        embed = discord.Embed(
            title="🔴  Do Not Disturb" if result.busy else "🟢  Come On In",
            description=(
                "They nodded twice — they're in a call. Please wait."
                if result.busy
                else "No signal — they're available. Go ahead!"
            ),
            color=discord.Color.red() if result.busy else discord.Color.green(),
        )
        embed.set_footer(text="Reachy Mini · Desk Gatekeeper")
        await interaction.edit_original_response(content=None, embed=embed)
