import discord

from discord import app_commands
from discord.ext import commands

from check import restricted_roles
from modules.connection.sys_control import perform_action


class ConfirmStopHostingView(discord.ui.View):

    def __init__(self, cog, requester: discord.Member):
        super().__init__(timeout=30)

        self.cog = cog
        self.requester = requester

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.requester.id

    @discord.ui.button(
        label="Confirmar apagado",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.cog.stop_task:
            return await interaction.response.send_message(
                "Ya hay una detencion del hosting en progreso.",
                ephemeral=True
            )

        self.cog.stop_task = True

        await interaction.response.edit_message(
            content="Deteniendo el hosting...",
            embed=None,
            view=None
        )

        try:
            success, result_msg = await perform_action("stop")

            colour = 0x206020 if success else 0xff0000
            title = (
                "Hosting detenido"
                if success
                else "No se pudo detener el hosting"
            )

            embed = discord.Embed(
                title=title,
                description=result_msg,
                colour=colour,
                timestamp=discord.utils.utcnow()
            )

            embed.set_footer(text="Paradise RP")

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        except Exception as e:
            embed = discord.Embed(
                title="Error al detener el hosting",
                description=f"```{e}```",
                colour=0xff0000
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        finally:
            self.cog.stop_task = False

    @discord.ui.button(
        label="Cancelar",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="Detencion del hosting cancelada.",
            embed=None,
            view=None
        )


class StopHosting(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.stop_task = False

    @app_commands.command(
        name="stophosting",
        description="Detiene el hosting del servidor."
    )
    @restricted_roles(["Admin"])
    async def stophosting(self, interaction: discord.Interaction):
        if self.stop_task:
            return await interaction.response.send_message(
                "Ya hay una detencion del hosting en progreso.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="Detener hosting",
            description=(
                "Confirma si deseas detener el hosting del servidor."
            ),
            colour=0xff9900
        )

        embed.set_footer(text="Paradise RP")

        await interaction.response.send_message(
            embed=embed,
            view=ConfirmStopHostingView(self, interaction.user),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(StopHosting(bot))