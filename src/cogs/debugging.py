import discord
from discord.ext import commands
from discord import app_commands
from config import DEV_GUILD_ID

class Debugging(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.guilds(discord.Object(id=DEV_GUILD_ID))
    @app_commands.command(name="update", description="Updates the command list")
    @app_commands.default_permissions(administrator=True)
    async def update_command(self, interaction: discord.Interaction, scope: str = "guild"):
        await interaction.response.defer(ephemeral=True)

        if scope == "global":
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"Synced `{len(synced)}` commands globally.")
        else:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            synced = await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"Synced `{len(synced)}` commands to this guild.")

    @app_commands.command(name="hello")
    async def hello_command(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello! {interaction.user.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Debugging(bot))

