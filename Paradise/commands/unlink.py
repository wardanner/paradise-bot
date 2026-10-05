import discord
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

async def pz_username_autocomplete(interaction: discord.Interaction, current: str):
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

class Unlink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="unlink",
        description="Unlinks a discord user to their Project Zomboid account."
    )
    @app_commands.describe(
        user="The discord user.",
        pz_username="The Project Zomboid username"
    )
    @app_commands.autocomplete(pz_username=pz_username_autocomplete)
    @restricted_roles(["Admin"])
    async def unlink(self, interaction: discord.Interaction, user: discord.Member, pz_username: str):
        await interaction.response.defer()
        
        embed_confirm = discord.Embed(
            colour=0xff9900,
            title="⛓️‍💥 Desvinculación",
            description=(
                f"Usuario/a: {user.mention}\n"
                f"Cuenta de PZ: `{pz_username}`"
            ),
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")

        view = View()

        btn_unlink = Button(
            label="⛓️‍💥 Desvincular", # Spainsh: Unlink
            style = ButtonStyle.success
        )

        async def unlink_callback(interaction: discord.Interaction):
            await interaction.response.defer()

            for item in view.children:
                item.disabled = True
            await interaction.edit_original_response(content="⏳ Por favor espera...", view=view)

            try: 
                conn = sqlite.connect(PATH_TO_DATABASE)
                conn.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}'")
                cur = conn.cursor()

                cur.execute("DELETE FROM user_link WHERE discord_id = ?", (user.id,))
                conn.commit()
                conn.close()

                embed_success = discord.Embed(
                    colour=0x00ff88,
                    title="⛓️‍💥 Desvinculado",
                    description=f"¡`{pz_username}` ha sido desvinculado con {user.mention}!",
                    timestamp=discord.utils.utcnow()
                ).set_footer(text="🌴 Paradise RP 🌴")

                await interaction.followup.send(embed=embed_success)
            except:
                await interaction.followup.send("No hay usuarios vinculados.")
            finally:
                # What's locals()
                if "conn" in locals():
                    conn.close()

        btn_unlink.callback = unlink_callback
        view.add_item(btn_unlink)

        btn_cancel = Button(
            label="🗑️ Cancelar",
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
    await bot.add_cog(Unlink(bot))
            

