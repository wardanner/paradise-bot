import discord
import os
from sqlcipher3 import dbapi2 as sqlite
from check import restricted_roles
from dotenv import load_dotenv
from discord import app_commands, ButtonStyle
from discord.ext import commands
from discord.ui import Button, View
from rcon.source.async_rcon import rcon

load_dotenv()
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")
IP_ADDRESS = os.getenv("IP_ADDRESS")
RCON_PORT = os.getenv("RCON_PORT")
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

PATH_TO_DATABASE = "data/pz_discord.db"

async def account_autocomplete(interaction: discord.Interaction, current: str):
    # namespace lets you access other arguments that have been filled
    target_user = interaction.namespace.user

    if target_user is None:
        return []
    
    linked = get_pz_usernames(target_user.id)

    matches = [
        name for name in linked
        if current in name
    ][:25]

    return [app_commands.Choice(name=name, value=name) for name in matches]
    
def get_pz_usernames(discord_id: int) -> list[str] | None:
    conn = sqlite.connect(PATH_TO_DATABASE)
    conn.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}'")
    conn.row_factory = sqlite.Row
    cur = conn.cursor()
    cur.execute("SELECT pz_username FROM user_link WHERE discord_id = ?", (discord_id,))
    rows = cur.fetchall()
    conn.close()

    return [row["pz_username"] for row in rows]

# TODO:
# Need to handle disconnected data but it's not important right now

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ban",
        description="Ban a player on Project Zomboid."
    )
    @app_commands.describe(
        user="Usuario de Discord a buscar",
        account="Cuenta de PZ a banear",
        reason="Motivo del baneo",
        duration="Duración del baneo en minutos",
        unban_method="¿Cómo se levantará el baneo?"
    )
    @app_commands.choices(unban_method=[
        app_commands.Choice(name="Manual", value="manual"),
        app_commands.Choice(name="Automático", value="automatic")
    ])
    @app_commands.autocomplete(account=account_autocomplete)
    @restricted_roles(["Admin"])
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        account: str,
        reason: str,
        duration: int,
        unban_method: app_commands.Choice[str]
    ):
        embed = discord.Embed(
            colour=0xff9900,
            title="⚠️ Confirmar Baneo",
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")
        
        # TODO:
        # duration has to be a positive integer

        if unban_method.value == "automatic":
            embed.description = (
                f"La cuenta `{account}` será baneada por `{duration}` minuto(s).\n"
                f"El desbaneo se realizará **automáticamente** al cumplirse el tiempo.\n\n"
                f"Motivo:\n```ansi\n\u001b[2;40m\u001b[2;33m[{reason}]\u001b[0m\n```\n"
                f"Ejecutado por {interaction.user.mention}"
            )
        elif unban_method.value == "manual":
            embed.description = (
                f"La cuenta `{account}` será baneada por `{duration}` minuto(s).\n"
                f"El desbaneo deberá ser realizado **manualmente** por un administrador.\n\n"
                f"Motivo:\n```ansi\n\u001b[2;40m\u001b[2;33m[{reason}]\u001b[0m\n```\n"
                f"Ejecutado por {interaction.user.mention}"
            )

        view = View()

        btn_confirm = Button(
            label="🔨 Banear",
            style=ButtonStyle.success
        )

        async def confirm_callback(interaction: discord.Interaction):
            # TODO:
            # Connect to database and insert all the ban info (ban_date, user, reason, unban_date, banned_by, is_active, etc)
            # Execute RCON command
            # Send a message to the ban channel
            # Notify admins if the user needs to be unbanned manually
            # Disable buttons


            await interaction.response.send_message("En progreso")

        btn_confirm.callback = confirm_callback
        view.add_item(btn_confirm)

        btn_cancel = Button(
            label="🗑️ Cancelar",
            style=ButtonStyle.danger
        )

        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.send_message("En progreso")

        btn_cancel.callback = cancel_callback
        view.add_item(btn_cancel)

        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Ban(bot))

    