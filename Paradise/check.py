import discord
from discord import app_commands

def restricted_roles(allowed: list[str]):
    async def predicate(interaction: discord.Interaction):
        if not any(role.name in allowed for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando.",
                ephemeral=True
            )
            print(f"CheckFailure: {interaction.user} tried to use /{interaction.command.name} without permission.")
            return False
        return True
    return app_commands.check(predicate)