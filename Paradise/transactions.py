# this file only works with Mod Data Dumper
import asyncssh
import asyncio
import discord
import json
import os
#import sqlite3
from sqlcipher3 import dbapi2 as sqlite
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()
TRANSACTION_CHANNEL_ID = int(os.getenv("TRANSACTION_CHANNEL_ID"))
SFTP_IP = os.getenv("SFTP_IP")
SFTP_PORT = os.getenv("SFTP_PORT")
SFTP_USERNAME = os.getenv("SFTP_USERNAME")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")

HISTORY_PATH = "data/transaction_history.json"
PATH_TO_DATABASE = "data/pz_discord.db"
PENDING_PATH = "/server-data/Lua/balance/pending_transactions.txt"
PROCESSING_PATH = "/server-data/Lua/balance/processing_transactions.json"

def update_transaction_history(tx, perspective):
    try:
        with open(HISTORY_PATH, "r") as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = {}

    entry = {
        "type": tx["type"],
        "sender": tx["sender"],
        "recipient": tx["recipient"],
        "coin": tx["coin"],
        "specialCoin": tx["specialCoin"],
        "timestamp": tx["timestamp"]
    }

    username = tx["sender"] if perspective == "sender" else tx["recipient"]

    if username not in history:
        history[username] = {"transactions": []}

    # FILO - newest first, max 10
    history[username]["transactions"].insert(0, entry)
    history[username]["transactions"] = history[username]["transactions"][:10]

    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)

# Makes sense to put pz_username as argument, we're reading from pending_transactions.json here
def get_discord_id(pz_username):
    conn = sqlite.connect(PATH_TO_DATABASE)
    conn.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}'")
    conn.row_factory = sqlite.Row
    cur = conn.cursor()
    cur.execute("SELECT discord_id FROM user_link WHERE pz_username = ?", (pz_username,))
    row = cur.fetchone()
    conn.close()
    return row["discord_id"] if row else None

async def get_or_create_thread(channel, pz_username, discord_id):
    discord_id = get_discord_id(pz_username)
    thread_name = f"{pz_username} ₴ {discord_id}"

    # Checks active threads
    for thread in channel.threads:
        if thread.name == thread_name:
            return thread
        
    # Checks archived thread
    async for thread in channel.archived_threads(private=True):
        if thread.name == thread_name:
            await thread.edit(archived=False)
            return thread

    # Is this thread going to live forever? No
    thread = await channel.create_thread(
        name=thread_name,
        type=discord.ChannelType.private_thread,
        invitable=False,
        auto_archive_duration=10080
    )
    await thread.send(f"Transacciones de {pz_username} ₴ <@{discord_id}>")
    return thread

def build_embed(tx, perspective):
    ts = tx["timestamp"]
    coin = tx["coin"]
    specialCoin = tx["specialCoin"]
    sender = tx["sender"]
    recipient = tx["recipient"]
    old = tx["oldBalance"]
    source = tx.get("source", "ingame")
    is_discord = source == "discord"
    accent_colour = None # 0x3498DB if is_discord else None
    source_tag = f"\n\n〣 Enviado desde Discord\n〢 ID: `{tx.get('id', 'N/A')}`" if is_discord else ""

    if tx["type"] == "Deposit":
        new_coin = old["senderCoin"] + coin
        new_special = old["senderSpecialCoin"] + specialCoin

        received_parts = []
        if coin > 0:
            received_parts.append(f"`{coin}` <:Coin:1485307466844733774>")
        if specialCoin > 0:
            received_parts.append(f"`{specialCoin}` <:PAmethyst:1485307391817027724>")

        lines = [f"`{sender}` depositó {' '.join(received_parts)}\n\n〣 Actualización de Monedas"]
        if coin > 0:
            lines.append(f"〢 `{old['senderCoin']}` → `{new_coin}` <:Coin:1485307466844733774> ↑")
        if specialCoin > 0:
            lines.append(f"〢 `{old['senderSpecialCoin']}` → `{new_special}` <:PAmethyst:1485307391817027724> ↑")
        lines.append(f"\n<t:{ts}:R>")

        return discord.Embed(
            colour=0xF1C40F,
            title="💳 Transferencia",
            description="\n".join(lines),
            timestamp=discord.utils.utcnow()
        ).set_footer(text=f"{sender} · Depósito")
    
    elif tx["type"] == "Transfer":
        if perspective == "sender":
            new_coin = old["senderCoin"] - coin
            new_special = old["senderSpecialCoin"] - specialCoin

            received_parts = []
            if coin > 0:
                received_parts.append(f"`{coin}` <:Coin:1485307466844733774>")
            if specialCoin > 0:
                received_parts.append(f"`{specialCoin}` <:PAmethyst:1485307391817027724>")

            lines = [f"`{sender}` transfirió {' '.join(received_parts)}\n\n〣 Actualización de Monedas"]
            if coin > 0:
                lines.append(f"〢 `{old['senderCoin']}` → `{new_coin}` <:Coin:1485307466844733774> ↓")
            if specialCoin > 0:
                lines.append(f"〢 `{old['senderSpecialCoin']}` → `{new_special}` <:PAmethyst:1485307391817027724> ↓")
            lines.append(f"\n<t:{ts}:R>")

            return discord.Embed(
                colour=accent_colour or 0xE74C3C,
                title=f"💳 Transferencia",
                description="\n".join(lines) + source_tag,
                timestamp=discord.utils.utcnow()
            ).set_footer(text=f"{sender} → {recipient}")
        
        elif perspective == "recipient":
            new_coin = old["recipientCoin"] + coin
            new_special = old["recipientSpecialCoin"] + specialCoin

            received_parts = []
            if coin > 0:
                received_parts.append(f"`{coin}` <:Coin:1485307466844733774>")
            if specialCoin > 0:
                received_parts.append(f"`{specialCoin}` <:PAmethyst:1485307391817027724>")

            lines = [f"`{recipient}` recibió {' '.join(received_parts)}\n\n〣 Actualización de Monedas"]
            if coin > 0:
                lines.append(f"〢 `{old['recipientCoin']}` → `{new_coin}` <:Coin:1485307466844733774> ↑")
            if specialCoin > 0:
                lines.append(f"〢 `{old['recipientSpecialCoin']}` → `{new_special}` <:PAmethyst:1485307391817027724> ↑")
            lines.append(f"\n<t:{ts}:R>")

            return discord.Embed(
                colour=accent_colour or 0x2ECC71,
                title=f"💳 Transferencia",
                description="\n".join(lines) + source_tag,
                timestamp=discord.utils.utcnow()
            ).set_footer(text=f"{sender} → {recipient}")
        
def build_failed_embed(tx):
    coin = tx["coin"]
    specialCoin = tx["specialCoin"]
    amount_parts = []

    if coin > 0:
        amount_parts.append(f"`{coin}` <:Coin:1485307466844733774>")
    if specialCoin > 0:
        amount_parts.append(f"`{specialCoin}` <:PAmethyst:1485307391817027724>")

    return discord.Embed(
        colour=0x6600cc,
        title="❌ Transferencia Fallida",
        description=(
            f"No se pudo completar la transferencia de {' '.join(amount_parts)} "
            f"a `{tx['recipient']}`.\n\n"
            f"〢 Motivo: {tx['reason']}\n\n"
            f"〣 Enviado desde Discord"
            f"〢 ID: `{tx.get('id', 'N/A')}`"
        ),
        timestamp=discord.utils.utcnow()
    ).set_footer(text=f"{tx['sender']} → {tx['recipient']}")
        
async def process_lines(bot, lines):
    channel = bot.get_channel(TRANSACTION_CHANNEL_ID)
    if not channel:
        print("Transaction channel not found!")
        return

    for line in lines:
        tx = json.loads(line)

        if tx["type"] == "Deposit":
            discord_id = get_discord_id(tx["sender"])
            if not discord_id:
                print(f"Skipping {tx['sender']} - not linked")
                continue
            thread = await get_or_create_thread(channel, tx["sender"], discord_id)
            await thread.send(embed=build_embed(tx, "sender"))
            update_transaction_history(tx, "sender")

        elif tx["type"] == "Transfer":
            sender_id = get_discord_id(tx["sender"])
            recipient_id = get_discord_id(tx["recipient"])

            if sender_id:
                thread = await get_or_create_thread(channel, tx["sender"], sender_id)
                await thread.send(embed=build_embed(tx, "sender"))
                update_transaction_history(tx, "sender")
            else:
                print(f"Skipping sender {tx['sender']} - not linked")

            if recipient_id:
                thread = await get_or_create_thread(channel, tx["recipient"], recipient_id)
                await thread.send(embed=build_embed(tx, "recipient"))
                update_transaction_history(tx, "recipient")
            else:
                print(f"Skipping recipient {tx['recipient']} - not linked")
        elif tx["type"] == "TransferFailed":
            sender_id = get_discord_id(tx["sender"])
            if sender_id:
                thread = await get_or_create_thread(channel, tx["sender"], sender_id)
                await thread.send(embed=build_failed_embed(tx))
            else:
                print(f"Skipping failed-tx notice for {tx['sender']} - not linked")
            
        
# For local testing
async def process_transaction(bot, file_path="pending_transactions.txt"):
    with open(file_path, "r") as f:
        lines = [l for l in f.read().strip().split("\n") if l]
    await process_lines(bot, lines)

def start_polling(bot):
    @tasks.loop(seconds=60)
    async def poll_transactions():
        try:
            async with asyncssh.connect(SFTP_IP, port=int(SFTP_PORT), username=SFTP_USERNAME, password=SFTP_PASSWORD) as ssh:
                async with ssh.start_sftp_client() as sftp:
                    try:
                        await sftp.stat(PENDING_PATH)
                    except asyncssh.SFTPError:
                        return
                    
                    # If I turn my bot off when it's processing and not finishing the process
                    # two files exist, and the renaming would fail
                    try:
                        await sftp.remove(PROCESSING_PATH)
                    except asyncssh.SFTPError:
                        pass

                    await sftp.rename(PENDING_PATH, PROCESSING_PATH)

                    async with await sftp.open(PROCESSING_PATH) as f:
                        content = await f.read()

                    await sftp.remove(PROCESSING_PATH)

            lines = [l for l in content.strip().split("\n") if l]
            await process_lines(bot, lines)

        except Exception as e:
            print(f"Poll error: {type(e).__name__}: {e}")

    @poll_transactions.before_loop
    async def before_poll():
        await bot.wait_until_ready()

    poll_transactions.start()