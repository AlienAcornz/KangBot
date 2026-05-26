import discord
from discord.ext import commands
from discord import app_commands
from functools import wraps
from config import DEV_GUILD_ID

def check_role_hierarchy(func):
    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, member: discord.Member, *args, **kwargs):

        if interaction.user == member: #If the person running the command is the same as the target user
            await interaction.response.send_message("You cannot moderate yourself!",ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This command must be used in a server where role hierarchy is available.",
                ephemeral=True
            )
            return

        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "You cannot moderate a member with a role equal to or higher than yours!",
                ephemeral=True
            )
            return
        
        #TODO Check if the bot has a lower role than the target
        
        return await func(self, interaction, member, *args, **kwargs)
    return wrapper

class Moderation(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command()
    @check_role_hierarchy
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = ""):
        await member.kick(reason=reason)
        ostream = f"Kicked {member.mention} for: {reason}" if reason != "" else f"Kicked {member.mention}"
        await interaction.response.send_message(ostream)

    @app_commands.command()
    @check_role_hierarchy
    async def softban(self, interaction: discord.Interaction, member: discord.Member, reason: str = ""):
        await member.ban(reason=reason)
        await member.unban(reason=reason)
        await interaction.response.send_message(f"{member.mention} softbanned!")

    @app_commands.command()
    async def hello(self, interaction: discord.Interaction):
        roles = interaction.user.roles if isinstance(interaction.user, discord.Member) else "No roles"
        await interaction.response.send_message(f"Hello! {interaction.user.mention}, {roles}", ephemeral=True)

    @app_commands.guilds(discord.Object(id=DEV_GUILD_ID))
    @app_commands.command(name="update", description="Updates the command list")
    async def update(self, interaction: discord.Interaction, scope: str = "guild"):
        await interaction.response.defer(ephemeral=True)

        if scope == "global":
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"Synced `{len(synced)}` commands globally.")
        else:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            synced = await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"Synced `{len(synced)}` commands to this guild.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))