import discord
from check import restricted_roles
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

lm_client = AsyncOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio" # Doesn't need a real key, just can't be empty
)

def build_ai_embed(prompt:str, answer: str) -> discord.Embed:
    embed = discord.Embed(
        colour=0x5865f2,
        title="✨ Gemma",
        timestamp=discord.utils.utcnow()
    ).set_footer(text="🌴 Paradise RP 🌴")

    embed.add_field(name="❓ Pregunta", value=f"```\n{prompt}\n```", inline=False)
    embed.add_field(name="🤖 Respuesta", value=f"```\n{answer}\n```", inline=False)

    return embed

conversation_history = {}

async def query_local_model(prompt: str, user_id: int) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "content": prompt
    })

    response = await lm_client.chat.completions.create(
        #model="mistralai/devstral-small-2-2512",
        model="google/gemma-4-12b-qat",
        messages=[
            {"role": "system", "content": "Tu nombre es Gemma. Eres el asistente oficial de Paradise RP. Eres sarcástico y tienes sentido del humor. Responde de forma breve y concisa. Máximo 2-3 oraciones. Responde siempre en el mismo idioma que el usuario."},
            *conversation_history[user_id]
        ]
    )
    
    answer = response.choices[0].message.content

    conversation_history[user_id].append({
        "role": "assistant",
        "content": answer
    })

    conversation_history[user_id] = conversation_history[user_id][-10:]

    return answer

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
            name="ai", 
            description="Ask something to the local model."
    )
    @restricted_roles(["Admin"])
    async def ai(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        ts = int(discord.utils.utcnow().timestamp())

        embed_loading = discord.Embed(
            colour=0x5865f2,
            title="🧠 Procesando tu pregunta...",
            description=(
                "El modelo está pensando en una respuesta…\n"
                f"Iniciado <t:{ts}:R>"
            ),
            timestamp=discord.utils.utcnow()
        ).set_footer(text="🌴 Paradise RP 🌴")
        
        loading_msg = await interaction.followup.send(embed=embed_loading)
        answer = await query_local_model(prompt, interaction.user.id)
        await loading_msg.edit(embed=build_ai_embed(prompt, answer))

async def setup(bot):
    await bot.add_cog(AI(bot))