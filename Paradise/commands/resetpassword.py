import discord
import os
#import sqlite3
from sqlcipher3 import dbapi2 as sqlite
from check import restricted_roles
from discord import app_commands
from discord.ext import commands
from discord.ui import View
from rcon.source.async_rcon import rcon
from dotenv import load_dotenv

load_dotenv()
IP_ADDRESS = os.getenv("IP_ADDRESS")
RCON_PORT = os.getenv("RCON_PORT")
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")

PATH_TO_DATABASE = "data/pz_discord.db"

class ResetPasswordModal(discord.ui.Modal):
    def __init__(self, character: str, view: discord.ui.View, select: discord.ui.Select):
        super().__init__(title=f"Cambio de Contraseña de {character}"[:40])
        self.view = view
        self.select = select
        self.character = character
        # New password
        self.new_password = discord.ui.TextInput(
            label="Nueva Contraseña",
            placeholder="Ingresa la nueva contraseña"
        )

        # Confirm
        self.confirm = discord.ui.TextInput(
            label="Confirmar Contraseña",
            placeholder="Repite la contraseña"
        )

        self.add_item(self.new_password)
        self.add_item(self.confirm)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.select.disabled = True

        # TODO
        # Send RCON commands
        try:
            await rcon(f"removeuserfromwhitelist {self.character}", host=IP_ADDRESS, port=int(RCON_PORT), passwd=RCON_PASSWORD)
            await rcon(f"adduser {self.character} {self.new_password.value}", host=IP_ADDRESS, port=int(RCON_PORT), passwd=RCON_PASSWORD)
        except Exception as e:
            await interaction.response.send_message(f"RCON Error: {e}")
            return

        embed_updated = discord.Embed(
            colour=0x00ff88,
            title="🔐 Contraseña Actualizada",
            description="Tu contraseña ha sido cambiada exitosamente. Por favor protege tus datos y no la compartas con nadie.",
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        # Must be called before anything else, this is the acknowledgement to the interaction
        await interaction.followup.send(embed=embed_updated)

        await interaction.message.edit(view=self.view)

        embed_information = discord.Embed(
            colour=0x3498db,
            title="ℹ️ Información de la cuenta",
            description="Tu contraseña ha sido cambiada, por favor protege tus datos y tu cuenta.",
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        embed_information.add_field(
            name="Usuario",
            value=f"`{self.character}`"
        )

        embed_information.add_field(
            name="Nueva contraseña",
            value=f"`{self.new_password.value}`"
        )
        try:
            await interaction.user.send(embed=embed_information)
        # Discord setting problem
        except discord.Forbidden:
            await interaction.followup.send(
                embed=embed_information,
                ephemeral=True
            )


class CharacterSelect(discord.ui.Select):
    def __init__(self, linked, original_user):
        self.original_user = original_user
        options = [discord.SelectOption(label=name) for name in linked]
        super().__init__(placeholder="Selecciona un personaje...", options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.original_user.id:
            await interaction.response.send_message("No puedes usar esto.", ephemeral=True)
            return
        
        chosen = self.values[0]
        # TODO
        # Check if they're online

        await interaction.response.send_modal(ResetPasswordModal(chosen, self.view, self))

class ResetPassword(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="resetpassword",
        description="Reset the password of a user on Project Zomboid"
    )
    @restricted_roles(["Admin", "Residente"])
    async def reset_password(self, interaction: discord.Interaction):
        # Connects to database
        conn = sqlite.connect(PATH_TO_DATABASE)
        conn.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}'")
        conn.row_factory = sqlite.Row
        cur = conn.cursor()
        cur.execute("SELECT pz_username FROM user_link WHERE discord_id = ?", (interaction.user.id,))
        rows = cur.fetchall()
        conn.close()

        if len(rows) == 0:
            await interaction.response.send_message("No tienes ningún personaje vinculado a Discord, comunícate con un administrador.")
        else:
            embed = discord.Embed(
                colour=0xff9900,
                title="🔓 Restablecer Contraseña",
                description="Por favor, cierra sesión en Project Zomboid antes de continuar y selecciona tu personaje en la lista desplegable a continuación.",
                timestamp=discord.utils.utcnow()
            ).set_footer(text="🌴 Paradise RP 🌴")

            linked = [row["pz_username"] for row in rows]

            view = View()
            view.add_item(CharacterSelect(linked, interaction.user))

            await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(ResetPassword(bot))