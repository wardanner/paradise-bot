import discord
from check import restricted_roles
from discord import app_commands
from discord.ext import commands

class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="rules",
        description="Sends the rules embed for users to read."
    )
    @restricted_roles(["Admin"])
    async def rules(self, interaction: discord.Interaction):
        await interaction.response.send_message("¡Usa este comando una sola vez!", ephemeral=True)
        embed = discord.Embed(
            colour=0x206020,
            title="📜 Obtén tu rol en Reglas",
            description="Usa el botón para confirmar tu compromiso con lo establecido y ver detalles adicionales referentes del servidor."
        ).set_footer(text="🌴 Paradise RP 🌴")

        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label="✅ Confirmar", # Spanish: Confirm
            style=discord.ButtonStyle.blurple,
            custom_id="rules_confirm"
        ))

        await interaction.channel.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Rules(bot))