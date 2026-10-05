# this file only works with Mod Data Dumper
import asyncssh
import discord
import os
import json
#import sqlite3
from sqlcipher3 import dbapi2 as sqlite
from check import restricted_roles
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View
from dotenv import load_dotenv

load_dotenv()
SFTP_IP = os.getenv("SFTP_IP")
SFTP_PORT = os.getenv("SFTP_PORT")
SFTP_USERNAME = os.getenv("SFTP_USERNAME")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")

PATH_TO_DATABASE = "data/pz_discord.db"
PATH_TO_TRANSACTION_HISTORY = "data/transaction_history.json"

async def get_coin_balance():
    try:
        async with asyncssh.connect(SFTP_IP, port=int(SFTP_PORT), username=SFTP_USERNAME, password=SFTP_PASSWORD) as ssh:
            async with ssh.start_sftp_client() as sftp:
                # await sftp.rename("/server-data/Lua/balance/coinbalance.txt", "/server-data/Lua/balance/coinbalance.json")
                # json only cares about the content of the string
                async with await sftp.open("/server-data/Lua/balance/coinbalance.txt") as f:
                    data = json.loads(await f.read())
        return data
    except Exception as e:
        print(f"SFTP error: {e}")
        return None
    
async def get_transaction_history(pz_username) -> str:
    with open(PATH_TO_TRANSACTION_HISTORY, "r") as f:
        history = json.load(f)

    lines = []

    user_data = history.get(pz_username, {})
    txs = user_data.get("transactions", [])

    if not txs:
        return "No tienes historial de transacciones."
    
    # Sort dicts first (there are some wrong data)
    txs_sorted = sorted(txs, key=lambda x: x["timestamp"])
    
    for tx in txs_sorted:
        coin = tx["coin"]
        specialCoin = tx["specialCoin"]
        sender = tx["sender"]
        recipient = tx["recipient"]
        timestamp = tx["timestamp"]

        received_parts = []

        if coin > 0:
            received_parts.append(f"`{coin}` <:Coin:1485307466844733774>")
        if specialCoin > 0:
            received_parts.append(f"`{specialCoin}` <:PAmethyst:1485307391817027724>")

        if tx["type"] == "Deposit":
            lines.append(f"<t:{timestamp}:R> `{sender}` depositó {' '.join(received_parts)} ↑")
        elif tx["type"] == "Transfer":
            if sender == pz_username:
                lines.append(f"<t:{timestamp}:R> `{sender}` → `{recipient}` {' '.join(received_parts)} ↓")
            elif recipient == pz_username:
                lines.append(f"<t:{timestamp}:R> `{recipient}` ← `{sender}` {' '.join(received_parts)} ↑")

    return "\n".join(lines)
    
async def fetch_accounts(interaction: discord.Interaction):
    # Connects to database
    conn = sqlite.connect(PATH_TO_DATABASE)
    conn.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}'")
    conn.row_factory = sqlite.Row
    cur = conn.cursor()
    cur.execute("SELECT pz_username FROM user_link WHERE discord_id = ?", (interaction.user.id,))
    rows = cur.fetchall()
    conn.close()

    return rows

class WalletView(discord.ui.View):
    def __init__(self, original_user, selected):
        super().__init__(timeout=None)
        self.original_user = original_user
        self.selected = selected

    @discord.ui.button(label="🏦 Billetera", style=discord.ButtonStyle.secondary)
    async def check_wallet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        self.check_wallet.disabled = True
        await interaction.edit_original_response(content="⏳ Cargando billetera... Por favor espera.", view=self)

        data = await get_coin_balance()
        if data is None:
            await interaction.followup.send("Error al conectar con el servidor. Intenta de nuevo. 🥦", ephemeral=True)
            return

        embed_wallet = discord.Embed(
            colour=0xe6e6e6,
            title="🏦 Billetera",
            description=f"Aquí están los fondos de `{self.selected}`.",
            timestamp=discord.utils.utcnow()
        ).add_field(
            name="<:Coin:1485307466844733774> Coin",
            value=f"`{data[self.selected]['coin']}`",
            inline=True
        ).add_field(
            name="<:PAmethyst:1485307391817027724> Special Coin",
            value=f"`{data[self.selected]['specialCoin']}`",
            inline=True
        ).set_footer(text="🌴 Paradise RP 🌴")


        self.check_wallet.disabled = False
        await interaction.edit_original_response(content="", embed=embed_wallet, view=self)

    @discord.ui.button(label="📙 Historial", style=discord.ButtonStyle.secondary) 
    async def check_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        self.check_history.disabled = True
        await interaction.edit_original_response(content="⏳ Cargando historial... Por favor espera.", view=self)

        history = await get_transaction_history(self.selected)

        embed_history = discord.Embed(
            colour=0x708090,
            title="📙 Historial",
            description=(
                f"〢**Transacciones recientes:**\n\n"
                f"{history}"
            ),
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        self.check_history.disabled = False
        await interaction.edit_original_response(content="", embed=embed_history, view=self)

class CharacterSelect(Select):
    def __init__(self, linked, original_user):
        self.original_user = original_user
        options = [discord.SelectOption(label=account) for account in linked]
        super().__init__(placeholder="Selecciona tu cuenta...", options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.original_user.id:
            await interaction.response.send_message("No puedes usar esto.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        selected = self.values[0]

        ts = int(discord.utils.utcnow().timestamp())
        
        embed_connecting = discord.Embed(
            colour=0x2ECC71,
            title="🥦 Conectando a Indifferent Broccoli",
            description=(
                f"Obteniendo el archivo JSON 📄\n"
                f"Ejecutando <t:{ts}:R>"
            ),
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        loading_msg = await interaction.followup.send(embed=embed_connecting, ephemeral=True)

        # Loads PZ account balance
        data = await get_coin_balance()
        
        try:
            data[selected]
        except KeyError as e:
            print(e)
            return await interaction.followup.send(f"`{selected}` no ha vinculado su billetera. ", ephemeral=True)
        

        embed_wallet = discord.Embed(
            colour=0xe6e6e6,
            title="🏦 Billetera",
            description=f"Aquí están los fondos de `{selected}`.",
            timestamp=discord.utils.utcnow()
        ).add_field(
            name="<:Coin:1485307466844733774> Coin",
            value=f"`{data[selected]["coin"]}`",
            inline=True
        ).add_field(
            name="<:PAmethyst:1485307391817027724> Special Coin",
            value=f"`{data[selected]["specialCoin"]}`",
            inline=True
        ).set_footer(text="🌴 Paradise RP 🌴")

        view = WalletView(self.original_user, selected)
        await loading_msg.edit(embed=embed_wallet, view=view)
        

class Wallet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="wallet",
        description="Checks the coins in your wallet."
    )
    @restricted_roles(["Admin", "Residente"])
    async def wallet(self, interaction: discord.Interaction):
        # Has to set ephemeral state here so the rest of the
        await interaction.response.defer(ephemeral=True)

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

        # Loads accounts here from the database
        accounts = await fetch_accounts(interaction)

        # TODO
        # Debug this
        if len(accounts) == 0:
            await interaction.followup.send("No tienes ningún personaje vinculado a Discord, comunícate con un administrador.", ephemeral=True)
            return

        loading_msg = await interaction.followup.send(embed=embed_loading, ephemeral=True)

        linked = [account["pz_username"] for account in accounts]

        view = View()
        view.add_item(CharacterSelect(linked, interaction.user))

        embed_select = discord.Embed(
            colour=0x003d66,
            title="👤 Selecciona tu cuenta",
            description="Selecciona tu personaje de Project Zomboid para ver tu billetera.",
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        await loading_msg.edit(embed=embed_select, view=view)

async def setup(bot):
    await bot.add_cog(Wallet(bot))