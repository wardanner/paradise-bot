import discord
#import sqlite3
import os
from sqlcipher3 import dbapi2 as sqlite
from check import restricted_roles
from discord import app_commands, ButtonStyle
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv

load_dotenv()

DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")

PATH_TO_DATABASE = "data/pz_discord.db"

class Link(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="link",
        description="Links a discord user to their Project Zomboid account."
    )
    @app_commands.describe(
        user="The discord user.",
        pz_username="Their Project Zomboid username."
    )
    @restricted_roles(["Admin"])
    async def link(self, interaction: discord.Interaction, user: discord.Member, pz_username: str):
        await interaction.response.defer()
        view = View()

        btn_link = Button(
            label = "🔗 Vincular", # Spanish: Link
            style = ButtonStyle.success
        )

        embed_confirm = discord.Embed(
            colour=0xff9900,
            title="⚠️ Confirmar Vinculación",
            description=(
                f"Usuario/a: {user.mention}\n"
                f"Cuenta de PZ: `{pz_username}`"
            ),
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        async def link_callback(interaction: discord.Interaction):
            await interaction.response.defer()

            # Disable buttons while processing
            for item in view.children:
                item.disabled = True
            await interaction.edit_original_response(content="⏳ Por favor espera...", view=view)
            
            try:
                conn = sqlite.connect(PATH_TO_DATABASE)
                conn.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}';")
                cur = conn.cursor()
                # Forces SQLite to use the older journal mode instead of WAL (Write-Ahead Logging),
                # which prevents -wal and -shm files from being created and ensures the file is
                # fully released after conn.close(). Must be set before any other queries.
                #conn.execute("PRAGMA journal_mode=DELETE")

                cur.execute("INSERT INTO user_link (discord_id, pz_username) VALUES (?, ?)", (user.id, pz_username))
                conn.commit()
                conn.close()

                embed_success = discord.Embed(
                    colour=0x00ff88,
                    title="🔗 Vinculado",
                    description=f"¡`{pz_username}` ha sido vinculado con {user.mention}!",
                    timestamp=discord.utils.utcnow()
                ).set_footer(text="🌴 Paradise RP 🌴")

                await interaction.followup.send(embed=embed_success)
            except:
                await interaction.followup.send("Esta cuenta ya está vinculada.")
            finally:
                if "conn" in locals():
                    conn.close()

        btn_link.callback = link_callback
        view.add_item(btn_link)

        btn_cancel = Button(
            label="🗑️ Cancelar", # Spanish: Cancel
            style=ButtonStyle.danger
        )

        async def cancel_callback(interaction: discord.Interaction):
            embed_cancel = discord.Embed(
                colour=0xff0000,
                title="❌ Cancelado",
                description="La acción ha sido cancelada.",
                timestamp=discord.utils.utcnow()
            ).set_footer(text="🌴 Paradise RP 🌴")

            for item in view.children:
                item.disabled = True
            await interaction.message.edit(view=view)

            await interaction.response.send_message(embed=embed_cancel)

        btn_cancel.callback = cancel_callback
        view.add_item(btn_cancel)

        await interaction.followup.send(
            embed=embed_confirm,
            view=view
        )

async def setup(bot):
    await bot.add_cog(Link(bot))