import asyncssh
import discord
import json
import uuid
import os
from check import restricted_roles
from discord import app_commands, ButtonStyle
from discord.ext import commands
from discord.ui import View, Button
from sqlcipher3 import dbapi2 as sqlite
from dotenv import load_dotenv

load_dotenv()
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")
SFTP_IP = os.getenv("SFTP_IP")
SFTP_PORT = os.getenv("SFTP_PORT")
SFTP_USERNAME = os.getenv("SFTP_USERNAME")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")

QUEUE_DIR = "server-data/Lua/queue"
QUEUE_LOG_PATH = f"{QUEUE_DIR}/queue_log.jsonl"
PATH_TO_DATABASE = "data/pz_discord.db"

async def recipient_autocomplete(interaction: discord.Interaction, current: str):
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

async def queue_transfer(sender: str, recipient: str, coin_type: str, amount: int) -> str:
    tx_id = uuid.uuid4().hex
    request = {
        "id": tx_id,
        "sender": sender,
        "recipient": recipient,
        "coinType": coin_type,
        "amount": amount
    }
    # Why use dumps?
    line = json.dumps(request) + "\n"

    async with asyncssh.connect(SFTP_IP, port=int(SFTP_PORT), username=SFTP_USERNAME, password=SFTP_PASSWORD) as ssh:
        async with ssh.start_sftp_client() as sftp:
            try:
                await sftp.stat(QUEUE_DIR)
            except asyncssh.SFTPError:
                await sftp.makedirs(QUEUE_DIR)
            # What's a?
            async with sftp.open(QUEUE_LOG_PATH, "a") as f:
                await f.write(line)

    return tx_id

class AccountSelect(discord.ui.Select):
    def __init__(self, linked, original_user, embed: discord.Embed, recipient: str, coin_type: str, amount: int):
        self.original_user = original_user
        self.embed = embed
        self.recipient = recipient
        self.coin_type = coin_type
        self.amount = amount

        options = [discord.SelectOption(label=name) for name in linked]
        super().__init__(placeholder="Selecciona una cuenta...", options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.original_user.id:
            await interaction.response.send_message("No puedes usar esto.", ephemeral=True)
            return
        
        chosen = self.values[0]

        if chosen == self.recipient:
            return await interaction.response.send_message("No puedes enviar una transferencia a ti mismo.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        if self.coin_type.value == "coin":
            coin_type_emoji = "<:Coin:1485307466844733774>"
        elif self.coin_type.value == "specialCoin":
            coin_type_emoji = "<:PAmethyst:1485307391817027724>"

        # TODO:
        # Add a confirmation message here
        # Edit the original embed
        embed = discord.Embed(
            colour=0xff9900,
            title="⚠️ Confirmar transacción",
            description=(
                f"¿Estás seguro de que quieres hacer esta transacción?\n\n"
                f"`{chosen}` → `{self.recipient}`\n\n"
                f"〢 Fondos transferidos: `{self.amount}` {coin_type_emoji}"
            ),
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        view = View()

        btn_confirm = Button(
            label="💸 Transferir",
            style=ButtonStyle.success
        )

        async def confirm_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            for item in view.children:
                item.disabled = True
            await interaction.edit_original_response(view=view)
            # The below line cannot find the message to edit because it's ephemral
            #await interaction.message.edit(view=view)
            tx_id = await queue_transfer(chosen, self.recipient, self.coin_type.value, self.amount)

            ts = int(discord.utils.utcnow().timestamp())

            embed = discord.Embed(
                colour=0x2ECC71,
                title="💸 Transferencia enviada",
                description=(
                    f"ID de transacción: `{tx_id}`\n"
                    f"Permite de 30 a 60 segundos para que la transacción finalice.\n"
                    f"Ejecutando <t:{ts}:R>"
                ),
                timestamp=discord.utils.utcnow()
            ).set_footer(text=f"{chosen} → {self.recipient}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        btn_confirm.callback = confirm_callback
        view.add_item(btn_confirm)

        btn_cancel = Button(
            label="🗑️ Cancelar",
            style=ButtonStyle.danger 
        )

        async def cancel_callback(interaction: discord.Interaction):
            # TODO
            # Add an embed
            # Disable both buttons
            for item in view.children:
                item.disabled = True
            await interaction.response.edit_message(view=view)
            # There's no response yet, so the below line would throw an error
            #await interaction.message.edit(view=view)

            await interaction.followup.send("La acción ha sido cancelada.", ephemeral=True)

        btn_cancel.callback = cancel_callback
        view.add_item(btn_cancel)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class Transfer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="transfer",
        description="Transfer funds to other users."
    )
    @app_commands.describe(
        user="Usuario de Discord destinatario.",
        recipient="Nombre de usuario de Project Zomboid del destinatario.",
        coin_type="Tipo de moneda a transferir.",
        amount="Cantidad a transferir."
    )
    @app_commands.choices(coin_type=[
        app_commands.Choice(name="Coin", value="coin"),
        app_commands.Choice(name="Special Coin", value="specialCoin")
    ])
    @app_commands.autocomplete(recipient=recipient_autocomplete)
    # Makes it an admin only command first
    @restricted_roles(["Admin", "Residente"])
    async def transfer(
        self, 
        interaction: discord.Interaction,
        user: discord.Member,
        recipient: str,
        coin_type: app_commands.Choice[str],
        amount: int,
    ):
        linked = get_pz_usernames(interaction.user.id)

        if len(linked) == 0:
            return await interaction.response.send_message("No tienes ningún personaje vinculado a Discord, comunícate con un administrador.", ephemeral=True)
        
        if user.id == interaction.user.id:
            return await interaction.response.send_message("No puedes enviar una transferencia a ti mismo.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)

        if amount <= 0:
            await interaction.followup.send(
                "❌ La cantidad debe ser mayor a 0.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            colour=0x003d66,
            title="👤 Selecciona tu Cuenta",
            description="Selecciona tu cuenta de Project Zomboid para continuar.",
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        view = View()
        view.add_item(AccountSelect(linked, interaction.user, embed, recipient, coin_type, amount))

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Transfer(bot))
        
