import discord
import os
import asyncio
#import sqlite3
from sqlcipher3 import dbapi2 as sqlite
from check import restricted_roles
from dotenv import load_dotenv
from discord import app_commands, ButtonStyle
from discord.ext import commands
from discord.ui import View, Button
from rcon.source.async_rcon import rcon

load_dotenv()
IP_ADDRESS = os.getenv("IP_ADDRESS")
RCON_PORT = os.getenv("RCON_PORT")
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
SFTP_IP = os.getenv("SFTP_IP")
SFTP_PORT = os.getenv("SFTP_PORT")
SFTP_USERNAME = os.getenv("SFTP_USERNAME")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")

PATH_TO_DATABASE = "data/pz_discord.db"

def load_text(filename: str) -> str:
    with open(f"data/texts/{filename}", "r", encoding="utf-8") as f:
        return f.read()

# Display Whitelist Modal
class WhitelistModal(discord.ui.Modal):
    def __init__(self, panel, target_user: discord.Member):
        super().__init__(title=f"Añadir usuario para {target_user.display_name}"[:45])
        self.panel = panel
        self.target_user = target_user

        # Username
        self.username = discord.ui.TextInput(
            label="Usuario",
            placeholder="Ej: Max_Rockatansky"
        )

        self.add_item(self.username)

        # Password
        self.password = discord.ui.TextInput(
            label="Contraseña",
            placeholder="La contraseña que usará para entrar"
        )

        self.add_item(self.password)

        # Confirm
        self.confirm = discord.ui.TextInput(
            label="Confirmar Contraseña",
            placeholder="Repite la contraseña"
        )

        self.add_item(self.confirm)

    # on_submit is not triggered if user cancels the modal
    async def on_submit(self, interaction: discord.Interaction):
        # Buys you 15 minutes because this process is too long
        await interaction.response.defer()

        # Disable buttons while processing
        for child in self.panel.children:
            if isinstance(child, discord.ui.Button) and child.label == "🖋️ Registrarse":
                child.disabled = True
        await interaction.message.edit(content="⏳ Por favor espera...", view=self.panel)

        # TODO: Validate the account and password confirmation
        # Validate password
        # A-Za-z0-9_

        if " " in self.username.value:
            # TODO: Change the embed name
            embed = discord.Embed(
                colour=0xff0000,
                title="❌ Fallido",
                description="Por favor, evita usar espacios en el nombre de usuario.",
                timestamp=discord.utils.utcnow()
            ).set_footer(text="🌴 Paradise RP 🌴")

            for child in self.panel.children:
                if isinstance(child, discord.ui.Button) and child.label == "🖋️ Registrarse":
                    child.disabled = False

            await interaction.followup.send(embed=embed)
            return await interaction.message.edit(view=self.panel)
        

        # create an account on Project Zomboid through RCON
        response = await rcon(f"adduser {self.username.value} {self.password.value}", host=IP_ADDRESS, port=int(RCON_PORT), passwd=RCON_PASSWORD)
        print(response)
        
        if "created" in response:
            # disable the register button ONLY after successful submit
            for child in self.panel.children:
                if isinstance(child, discord.ui.Button) and child.label == "🖋️ Registrarse":
                    child.label = "✔️ Registrado"
                    child.disabled = True

            try:
                conn = sqlite.connect(PATH_TO_DATABASE)
                conn.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}'")
                cur = conn.cursor()
                #conn.execute("PRAGMA journal_mode=DELETE")
                cur.execute("INSERT INTO user_link (discord_id, pz_username) VALUES (?, ?)", (interaction.user.id, self.username.value))
                conn.commit()
                conn.close()
            except Exception as e:
                conn.close()
                # Catch any other unexpected errors
                await interaction.followup.send(f"Ocurrió un error: {e}")
            finally:
                if "conn" in locals():
                    conn.close()

            await interaction.message.edit(view=self.panel)

            embed_account_created = discord.Embed(
                colour=0x00ff88,
                title="🎉 Cuenta creada",
                description=(
                    f"✅ ¡El usuario `{self.username.value}` fue creado con exito para {self.target_user.mention}!\n\n"
                    f"🔗 El discord ha sido vinculado/añadido al jugador `{self.username.value}`.\n\n"
                    "ℹ️ Por favor, revisa tu mensaje directo o mensaje temporal para obtener información de la cuenta."
                ),
                timestamp=discord.utils.utcnow()
            ).set_footer(text="🌴 Paradise RP 🌴")

            await interaction.followup.send(
                embed=embed_account_created,
                ephemeral=False
            )

            embed_account_information = discord.Embed(
                colour=0x3498db,
                title="ℹ️ Información de la cuenta",
                description=(
                    "🌴 Bienvenido a Paradise 🌴\n"  
                    "Por favor, protege tus datos y tu cuenta."
                ),
                timestamp=discord.utils.utcnow()
            ).set_footer(text="🌴 Paradise RP 🌴")

            embed_account_information.add_field(
                name="Usuario",
                value=f"`{self.username.value}`",
                inline=True
            )

            embed_account_information.add_field(
                name="Contraseña",
                value=f"`{self.password.value}`"
            )

            try:
                await interaction.user.send(embed=embed_account_information)
            except discord.Forbidden:
                await interaction.followup.send(embed=embed_account_information)
        else:
            embed = discord.Embed(
                colour=0xff0000,
                title="❌ Fallido",
                description=f"Mensaje de error:\n```{response}```",
                timestamp=discord.utils.utcnow()
            ).set_footer(text="🌴 Paradise RP 🌴")

            for child in self.panel.children:
                if isinstance(child, discord.ui.Button) and child.label == "🖋️ Registrarse":
                    child.disabled = False

            await interaction.message.edit(view=self.panel)
            await interaction.followup.send(embed=embed)

# Display Whitelist Panel (2 buttons)
class WhitelistPanel(View):
    def __init__(self, target_user: discord.Member):
        super().__init__(timeout=None)
        self.target_user = target_user
        self.register_button: Button | None = None

    # TODO
    # Make this button available to the welcomed user only
    @discord.ui.button(
        label="🖋️ Registrarse", # Spanish: Register
        style=ButtonStyle.success
    )
    async def register_callback(self, interaction: discord.Interaction, button: Button):
        self.register_button = button
        await interaction.response.send_modal(WhitelistModal(self, self.target_user))

    @discord.ui.button(
        label="🛠️ Reactivar", # Spanish: Reactivate
        style=ButtonStyle.primary
    )
    async def reactivate_callback(self, interaction: discord.Interaction, button: Button):
        # Edit the line below to add/remove roles
        allowed_roles = {"Admin", "Aspirante"}
        user_roles = {role.name for role in interaction.user.roles}

        if not (allowed_roles & user_roles):
            await interaction.response.send_message(
                "❌ No tienes permisos para usar este botón.",
                ephemeral=True
            )
            return
        
        # Checks if the button has been clicked
        if self.register_button:
            self.register_button.disabled = False
            self.register_button.label = "🖋️ Registrarse"

            await interaction.response.edit_message(view=self)

            await interaction.followup.send(
                "🛠️ Botón Reactivado.",
                ephemeral=True
            )

    @discord.ui.button(
        label="🚫 Deactivar", # Spanish: Deactivate,
        style=ButtonStyle.danger
    )
    async def deactivate_callback(self, interaction: discord.Interaction, button: Button):
        # Edit the line below to add/remove roles
        allowed_roles = {"Admin", "Aspirante"}
        user_roles = {role.name for role in interaction.user.roles}

        if not (allowed_roles & user_roles):
            await interaction.response.send_message(
                "❌ No tienes permisos para usar este botón.",
                ephemeral=True
            )
            return

        self.register_button.disabled=True
        self.register_button.label="🖋️ Registrarse"

        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            "🚫 Button Deactivated",
            ephemeral=True
        )

# Display Review Panel (4 buttons)
class ReviewPanel(View):
    def __init__(self, target_user: discord.Member):
        super().__init__(timeout=None)
        self.target_user = target_user

    # Bienvenido button
    @discord.ui.button(
        label="👋 Bienvenido", # Spanish: Welcome
        style=ButtonStyle.secondary
    )
    async def welcome_callback(self, interaction: discord.Interaction, button: Button):
        content = f"Saludos {self.target_user.mention} ¡Te damos una calida bienvenida a nuestro servidor!"
        description = load_text("bienvenido.txt")

        embed_bienvenido = discord.Embed(
            colour=0x206020,
            description=description,
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        embed_preguntas_de_rol = discord.Embed(
            colour=0x206020,
            description=load_text("preguntas_de_rol.txt"),
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        await interaction.response.send_message(content, embed=embed_bienvenido)

        try:
            async with interaction.channel.typing():
                await asyncio.sleep(1.5)
        except discord.DiscordServerError:
            await asyncio.sleep(1.5)
        await interaction.followup.send(embed=embed_preguntas_de_rol)
        
        
        
    # Lista blanca button
    @discord.ui.button(
        label="📝 Lista blanca", # Spanish: Whitelist
        style=ButtonStyle.secondary
    )
    async def whitelist_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            f"Atentido por {interaction.user.mention}"
        )

        content = "¡Gracias por tu respuestas!"
        description = load_text("lista_blanca.txt")

        embed = discord.Embed(
            colour=0x206020,
            description=description,
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        await interaction.followup.send(
            content,
            embed=embed,
            view=WhitelistPanel(self.target_user)
        )

    # Punto de Partida button
    @discord.ui.button(
        label="🧭 Punto de Partida", # Spanish: Starting Point
        style=ButtonStyle.secondary
    )
    async def starting_point_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        description = load_text("punto_de_partida.txt")

        sobreviviente = discord.utils.get(interaction.guild.roles, name="Sobreviviente")

        embed_punto_de_partida = discord.Embed(
            colour=0x206020,
            description=description,
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        embed_roles = discord.Embed(
            title="✅ Roles Actualizados",
            colour=0x206020,
            description=(
                f"**Usuario:** {self.target_user.mention}\n" 
                f"**Role añadido:** {sobreviviente.mention}\n"
                #f"**Roles eliminados:** `{fantasma.name}`"
            ),
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")
        

        await self.target_user.add_roles(sobreviviente)
        #await self.target_user.remove_roles(fantasma)

        await interaction.followup.send(embed=embed_roles)

        # Discord server-side error (500) Discord's API can hiccup when trying
        # to send the typing indicator.
        try:
            async with interaction.channel.typing():
                await asyncio.sleep(1.5)
        except discord.DiscordServerError:
            await asyncio.sleep(1.5)
        await interaction.followup.send(embed=embed_punto_de_partida)

    # Recomendaciones button
    @discord.ui.button(
        label="💡 Recomendaciones", # Spanish: Recommendations
        style=ButtonStyle.secondary
    )
    async def recommendations_callback(self, interaction: discord.Interaction, button: Button):
        description = load_text("recomendaciones.txt")

        embed = discord.Embed(
            colour=0x206020,
            description=description,
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        await interaction.response.send_message(embed=embed)

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # TODO
    # Translate the description in Spanish
    @app_commands.command(
        name="welcome", 
        description="Welcome a user to Paradise!"
    )
    @app_commands.describe(
        user="The user to welcome."
    )
    # Edit this line to add/remove allowed roles
    @restricted_roles(["Admin", "Aspirante"])
    async def welcome(self, interaction: discord.Interaction, user: discord.Member):
        view = View()

        btn_review = Button(
            label="🔍 Revisar", # Spanish: Review
            style=ButtonStyle.secondary
        )

        async def review_callback(interaction: discord.Interaction):
            # Edit the line below to add/remove roles
            allowed_roles = {"Admin", "Aspirante"}
            user_roles = {role.name for role in interaction.user.roles}

            if not (allowed_roles & user_roles):
                await interaction.response.send_message(
                    "❌ No tienes permisos para usar este botón.",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"Panel de control efímero {interaction.user.mention}:",
                view=ReviewPanel(user),
                ephemeral=True    
            )

        btn_review.callback = review_callback
        view.add_item(btn_review)

        btn_lock = Button(
            label="🔒 Bloquear", # Spanish: Lock
            style=ButtonStyle.danger
        )

        # TODO
        # Add the function here
        async def close_callback(interaction: discord.Interaction):
            # Edit the line below to add/remove roles
            allowed_roles = {"Admin", "Aspirante"}
            user_roles = {role.name for role in interaction.user.roles}

            if not (allowed_roles & user_roles):
                await interaction.response.send_message(
                    "❌ No tienes permisos para usar este botón.",
                    ephemeral=True
                )
                return
            
            btn_review.disabled = True
            await interaction.message.edit(view=view)

            await interaction.response.send_message(
                f"🔒 El botón Revisar ha sido bloqueado.",
                ephemeral=True
            )

        btn_lock.callback = close_callback
        view.add_item(btn_lock)

        await interaction.response.send_message(
            f"Manager para {user.mention} usuario",
            view=view
        )

async def setup(bot):
    await bot.add_cog(Welcome(bot))