import discord
import os
from check import restricted_roles
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from rcon.source.async_rcon import rcon


load_dotenv()
IP_ADDRESS = os.getenv("IP_ADDRESS")
RCON_PORT = os.getenv("RCON_PORT")
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="status",
        description="Checks the status of Project Zomboid server."
    )
    @restricted_roles(["Admin"])
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer()


        embed_online = discord.Embed(
            colour=0x00ff88,
            title="📡 Estado del Servidor",
            description="```ansi\n\u001b[2;40m\u001b[2;32m[OK]\u001b[0m\u001b[2;40m\u001b[0m El servidor está activo.\n```",
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        embed_offline = discord.Embed(
            colour=0xff0000,
            title="📡 Estado del Servidor",
            description="```ansi\n\u001b[2;40m\u001b[2;31m[ERROR]\u001b[0m\u001b[2;40m\u001b[0m El servidor está inactivo.\n```",
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        try:
            await rcon("players", host=IP_ADDRESS, port=int(RCON_PORT), passwd=RCON_PASSWORD)
            await interaction.followup.send(embed=embed_online)
        except Exception as e:
            await interaction.followup.send(embed=embed_offline)

async def setup(bot):
    await bot.add_cog(Status(bot))