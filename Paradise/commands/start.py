import discord

from discord import app_commands
from discord.ext import commands

from check import restricted_roles
from modules.connection.sys_control import perform_action


class ConfirmStartHostingView(discord.ui.view): #BlanquitaSeuestradaAyudenla

    def __init__(self, cog, requester: discord.member):
        super().__init__(timeout=30)

        self.cog = cog
        self.requester = requester

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.requester.id
    
    @discord.ui.button(
        label="Confirmar encendido",
        style=discord.ButtonStyle.success
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.cog.start_task:
            return await interaction.response.send_message(
                "Ya hay un encendido en el hosting en progreso.",
                ephemeral=True
            )
        
        self.cog.start_task = True

        await interaction.response.edit_message(
            content="Encendiendo el hosting . . .",
            embed=None,
            view=None
        )

        try:
            success, result_msg =await perform_action("start")

            colour = 0x206020 if success else 0xff0000
            title = (
                "Hosting Encendido"
                if success
                else "No se pudo encender el hosting"
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
                title="Error al encender el hosting",
                description=f"```{e}```",
                colour=0xff0000
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        finally:
            self.cog.start_task = False

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
                content="Encendido del hosting cancelado",
                embed=None,
                view=None
            )


class StartHosting(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.start_task = False

    @app_commands.command(
        name="starthosting",
        description="Enciende el hosting del servidor."
    )
    @restricted_roles(["Admin"])
    async def starthosting(self, interaction: discord.Interaction):
        if self.start_task:
            return await interaction.response.send_message(
                "Ya hay un encendido del hosting en progreso.",
                ephemeral=True
            )
        
        embed = discord.Embed(
            title="Encender hosting",
            description=(
                "Confirma si deseas encender el hosting del servidor."
            ),
            colour=0x206020
        )

        embed.set_footer(text="Paradise RP")

        await interaction.response.send_message(
            embed=embed,
            view=ConfirmStartHostingView(self, interaction.user),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(StartHosting(bot))