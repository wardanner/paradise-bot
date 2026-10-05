import discord
import asyncio

from discord.ext import commands
from discord import app_commands

from check import restricted_roles

from modules.connection.sys_control import (
    perform_action,
    send_rcon_command
)

ANNOUNCE_CHANNEL_ID = 1094881422612906096
PING_ROLE_ID = 1543791136177524776


class ConfirmRestartView(discord.ui.View):

    def __init__(self, parent_view, minutes):
        super().__init__(timeout=30)

        self.parent_view = parent_view
        self.minutes = minutes

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):

        return (
            interaction.user.id
            == self.parent_view.requester.id
        )

    @discord.ui.button(
        label="✅ Confirmar",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        cog = self.parent_view.cog

        if cog.restart_task:

            return await interaction.response.send_message(
                "❌ Ya hay un reinicio en progreso.",
                ephemeral=True
            )

        cog.restart_task = True

        await interaction.response.edit_message(
            content="✅ Reinicio iniciado correctamente.",
            embed=None,
            view=None
        )

        asyncio.create_task(
            self.parent_view.execute_restart(
                interaction,
                self.minutes
            )
        )

    @discord.ui.button(
        label="❌ Cancelar",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.edit_message(
            content="❌ Reinicio cancelado.",
            embed=None,
            view=None
        )


class RestartView(discord.ui.View):

    def __init__(
        self,
        cog,
        requester: discord.Member
    ):
        super().__init__(timeout=60)

        self.cog = cog
        self.requester = requester

    async def interaction_check(
        self,
        interaction
    ):

        return (
            interaction.user.id
            == self.requester.id
        )

    async def send_confirmation(
        self,
        interaction,
        minutes
    ):

        embed = discord.Embed(
            title="⚠️ Confirmar Reinicio",
            description=(
                f"¿Deseas reiniciar el servidor "
                f"en **{minutes} minuto(s)**?"
            ),
            colour=0xffcc00
        )

        embed.set_footer(
            text="🌴 Paradise RP 🌴"
        )

        await interaction.response.edit_message(
            embed=embed,
            view=ConfirmRestartView(
                self,
                minutes
            )
        )

    async def execute_restart(
        self,
        interaction,
        minutes
    ):

        channel = self.cog.bot.get_channel(
            ANNOUNCE_CHANNEL_ID
        )

        seconds = minutes * 60

        # Compute the absolute deadline before sleep
        deadline = int(discord.utils.utcnow().timestamp()) + seconds

        restart_embed = discord.Embed(
            title="🔄 Reinicio Programado",
            description=(
                f"El servidor se reiniciará "
                f"<t:{deadline}:R>\n\n"
                f"🧑 Solicitado por "
                f"{interaction.user.mention}\n\n"
                f"⚠️ Guarda tus pertenencias "
                f"y busca un lugar seguro."
            ),
            colour=0xff9900,
            timestamp=discord.utils.utcnow()
        )

        restart_embed.set_footer(
            text="🌴 Paradise RP 🌴"
        )

        restart_message = await channel.send(
            content=f"<@&{PING_ROLE_ID}>",
            embed=restart_embed
        )

        restart_sent = False

        try:

            # MENSAJE INICIAL
            if minutes == 0:

                await send_rcon_command(
                    'servermsg "[SERVER] Reinicio inmediato del servidor."'
                )

            else:

                await send_rcon_command(
                    f'servermsg "[SERVER] Reinicio programado en {minutes} minuto(s)."'
                )

            # COUNTDOWN
            while seconds > 0:

                await asyncio.sleep(5)

                seconds -= 5

                if seconds < 0:
                    seconds = 0

                # new_timestamp = (
                #    int(discord.utils.utcnow().timestamp())
                #    + seconds
                #)

                updated_embed = discord.Embed(
                    title="🔄 Reinicio Programado",
                    description=(
                        f"El servidor se reiniciará "
                        f"<t:{deadline}:R>\n\n"
                        f"🧑 Solicitado por "
                        f"{interaction.user.mention}\n\n"
                        f"⚠️ Guarda tus pertenencias "
                        f"y busca un lugar seguro."
                    ),
                    colour=0xff9900,
                    timestamp=discord.utils.utcnow()
                )

                updated_embed.set_footer(
                    text="🌴 Paradise RP 🌴"
                )

                try:

                    await restart_message.edit(
                        embed=updated_embed
                    )

                except:
                    pass

            # BORRAR MENSAJE COUNTDOWN
            try:
                ...
                # await restart_message.delete()

            except:
                pass

            # EMBED FINAL
            final_embed = discord.Embed(
                title="✅ Reinicio Iniciado",
                description=(
                    "El servidor comenzará "
                    "su proceso de reinicio."
                ),
                colour=0x206020,
                timestamp=discord.utils.utcnow()
            )

            final_embed.set_footer(
                text="🌴 Paradise RP 🌴"
            )

            await channel.send(
                content=f"<@&{PING_ROLE_ID}>",
                embed=final_embed
            )

            # SAVE
            await send_rcon_command("save all")

            await asyncio.sleep(5)

            await send_rcon_command(
                'servermsg "[SERVER] Guardando mundo..."'
            )

            await asyncio.sleep(5)

            await send_rcon_command(
                'servermsg "[SERVER] Reinicio del servidor iniciado..."'
            )

            # PROTECCIÓN ANTI DUPLICADO
            if not restart_sent:

                restart_sent = True

                await asyncio.sleep(30)

                success, result_msg = await perform_action(
                    "restart"
                )

                if not success:

                    error_embed = discord.Embed(
                        title="❌ Error al reiniciar",
                        description=result_msg,
                        colour=0xff0000
                    )

                    await channel.send(
                        embed=error_embed
                    )

                    return

            # ESPERAR ENCENDIDO

            # Added another 120 seconds as Alex requested
            await asyncio.sleep(120 + 120)

            online_embed = discord.Embed(
                title="🌴 PARADISE ONLINE",
                description=(
                    "El servidor ya se encuentra "
                    "disponible."
                ),
                colour=0x00ff88,
                timestamp=discord.utils.utcnow()
            )

            online_embed.set_footer(
                text="🌴 Paradise RP 🌴"
            )

            await channel.send(
                content=f"<@&{PING_ROLE_ID}>",
                embed=online_embed
            )

        except Exception as e:

            error_embed = discord.Embed(
                title="❌ Error en el reinicio",
                description=f"```{e}```",
                colour=0xff0000
            )

            await channel.send(
                embed=error_embed
            )

        finally:

            self.cog.restart_task = False

    @discord.ui.button(
        label="⚡ Ahora",
        style=discord.ButtonStyle.danger
    )
    async def instant_restart(
        self,
        interaction,
        button
    ):

        await self.send_confirmation(
            interaction,
            0
        )

    @discord.ui.button(
        label="🕐 1 Min",
        style=discord.ButtonStyle.secondary
    )
    async def one_minute(
        self,
        interaction,
        button
    ):

        await self.send_confirmation(
            interaction,
            1
        )

    @discord.ui.button(
        label="🕔 5 Min",
        style=discord.ButtonStyle.primary
    )
    async def five_minutes(
        self,
        interaction,
        button
    ):

        await self.send_confirmation(
            interaction,
            5
        )

    @discord.ui.button(
        label="🕙 10 Min",
        style=discord.ButtonStyle.success
    )
    async def ten_minutes(
        self,
        interaction,
        button
    ):

        await self.send_confirmation(
            interaction,
            10
        )

    @discord.ui.button(
        label="❌ Cancelar",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction,
        button
    ):

        await interaction.response.edit_message(
            content="❌ Reinicio cancelado.",
            embed=None,
            view=None
        )


class Restart(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.restart_task = False

    @app_commands.command(
        name="restart",
        description="Programa un reinicio del servidor."
    )
    @restricted_roles(["Admin", "Aspirante"])
    async def restart(
        self,
        interaction: discord.Interaction
    ):

        if self.restart_task:

            return await interaction.response.send_message(
                "❌ Ya hay un reinicio en progreso.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🔧 Panel de Reinicio",
            description=(
                "Selecciona en cuánto tiempo "
                "quieres reiniciar el servidor."
            ),
            colour=0x206020
        )

        embed.set_footer(
            text="🌴 Paradise RP 🌴"
        )

        await interaction.response.send_message(
            embed=embed,
            view=RestartView(
                self,
                interaction.user
            ),
            ephemeral=True
        )


async def setup(bot):

    await bot.add_cog(
        Restart(bot)
    )