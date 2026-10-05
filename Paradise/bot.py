import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from transactions import process_transaction, start_polling


intents = discord.Intents.all()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Add slash commands here
async def load_extensions():
    await bot.load_extension("commands.welcome")
    await bot.load_extension("commands.online")
    await bot.load_extension("commands.restart")
    await bot.load_extension("commands.start_hosting")
    await bot.load_extension("commands.stop_hosting")
    await bot.load_extension("commands.link")
    await bot.load_extension("commands.unlink")
    await bot.load_extension("commands.resetpassword")
    await bot.load_extension("commands.status")
    await bot.load_extension("commands.wallet")
    await bot.load_extension("commands.transfer")
    await bot.load_extension("commands.ban")
    await bot.load_extension("commands.ai")
    await bot.load_extension("commands.rules")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Active servers:")
    for guild in bot.guilds:
        print(f"- {guild.name} (id: {guild.id})")

    start_polling(bot)

    try:
        await load_extensions()
    except Exception as e:
        print("Extension load error:", e)

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print("Sync error:", e)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        # Leave empty for now
        return
    else:
        print(f"App command error: {error}")

@bot.command()
async def test_transactions(ctx):
    await process_transaction(bot)
    await ctx.send("Done!")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data["custom_id"] == "rules_confirm":
            await interaction.response.send_message(
                "Has confirmado tu compromiso con las reglas. ✅",
                ephemeral=True
            )
            reglas = discord.utils.get(interaction.guild.roles, name="✅ Reglas")
            await interaction.user.add_roles(reglas)

# Might have to move this line higher so this bot can connect to RCON
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

bot.run(TOKEN)
