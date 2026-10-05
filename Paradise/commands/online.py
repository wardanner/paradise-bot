import discord
import os
import re
#import sqlite3
from sqlcipher3 import dbapi2 as sqlite
from check import restricted_roles
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands
from rcon.source.async_rcon import rcon

# Rename this maybe
PATH_TO_DATABASE = "data/pz_discord.db"

load_dotenv()
IP_ADDRESS = os.getenv("IP_ADDRESS")
RCON_PORT = os.getenv("RCON_PORT")
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

SFTP_IP = os.getenv("SFTP_IP")
SFTP_PORT = os.getenv("SFTP_PORT")
SFTP_USERNAME = os.getenv("SFTP_USERNAME")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")

class Online(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="online",
        description="Display online players."
    )
    @restricted_roles(["Admin", "Aspirante"])
    async def online(self, interaction: discord.Interaction):
        # Immediately acknowledge so Discord doesn't timeout
        await interaction.response.defer()

        ts = int(discord.utils.utcnow().timestamp())

        embed_loading = discord.Embed(
            colour=0x0099ff,
            title="📂 Lista de Jugadores Cargando",
            description=(
                "Obteniendo jugadores desde la base de datos…\n"
                f"Ejecutando <t:{ts}:R>"
            ),
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        loading_msg = await interaction.followup.send(embed=embed_loading)

        try:
            # Delete this line
            # raise Exception("xddd")
            # Waits for async work to finish
            description = await self.fetch_and_format_players()
        except Exception as e:
            # TODO
            # Temporary fix, redesign this in the future 
            embed_error = discord.Embed(
                colour=0xff0000,
                title="❌ ¡Ups! Algo salió mal",
                description=(
                    "Error: no se pudieron recuperar los datos de los jugadores. Indifferent Broccoli o Paradise está fuera de servicio."
                )
            )            
            await loading_msg.edit(embed=embed_error)
            return
    
        embed_display = discord.Embed(
            colour=0x206020,
            description=f"{description}",
            timestamp=discord.utils.utcnow()
        ).set_author(
            name="Paradise",
            icon_url=self.bot.user.display_avatar
        ).set_footer(text="🌴 Paradise RP 🌴")

        await loading_msg.edit(embed=embed_display)

    # TODO
    # Rewrite the function so it returns a string list
    async def fetch_and_format_players(self) -> str:
        response = await rcon("players", host=IP_ADDRESS, port=int(RCON_PORT), passwd=RCON_PASSWORD)

        # Connects to database
        conn = sqlite.connect(PATH_TO_DATABASE)
        conn.row_factory = sqlite.Row
        conn.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}';")
        cur = conn.cursor()

        cur.execute("SELECT discord_id, pz_username FROM user_link")
        rows = cur.fetchall()

        # Disconnects from database
        conn.close()

        # Collects players and assigns tags
        online_players = {}
        description = ""
        players = response.split("\n")
        text = players.pop(0)

        # Remove the last element, it is an empty string
        players = players[:-1]

        match = re.search(r"\((\d+)\)", text)

        player_count = match.group(1) if match else "0"

        description += f"**{player_count} / 32 conecados**\n\n"

        # Rewrite this 
        lookup = {row["pz_username"]: row["discord_id"] for row in rows}

        for player in players:
            player = player.lstrip("-")
            online_players[player] = lookup.get(player)

        for pz_username, discord_id in online_players.items():
            if discord_id is None:
                description += f"◇ `{pz_username}` ⇎\n"
            else:
                user: discord.User = await self.bot.fetch_user(discord_id)
                description += f"◈ `{pz_username}` ⇔ {user.mention}\n"

        description.rstrip("\n")

        return description

async def setup(bot):
    await bot.add_cog(Online(bot))     