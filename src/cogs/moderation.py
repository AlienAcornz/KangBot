import discord
from discord.ext import commands
from discord import app_commands
from functools import wraps
from config import DEV_GUILD_ID
from src.services.db_service import db

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

    @app_commands.command(name="kick", description="Kicks a user")
    @check_role_hierarchy
    @app_commands.default_permissions(administrator=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = ""):
        await member.kick(reason=reason)
        ostream = f"Kicked {member.mention} for: {reason}" if reason != "" else f"Kicked {member.mention}"
        await interaction.response.send_message(ostream)

    @app_commands.command(name="softban", description="Temporarily bans and then unbans a user")
    @check_role_hierarchy
    @app_commands.default_permissions(administrator=True)
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
    @app_commands.default_permissions(administrator=True)
    async def update(self, interaction: discord.Interaction, scope: str = "guild"):
        await interaction.response.defer(ephemeral=True)

        if scope == "global":
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"Synced `{len(synced)}` commands globally.")
        else:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            synced = await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"Synced `{len(synced)}` commands to this guild.")

    @app_commands.guilds(discord.Object(id=DEV_GUILD_ID))
    @app_commands.command(name="add-note", description="Adds a note to a user")
    @app_commands.default_permissions(administrator=True)
    async def add_note(self, interaction: discord.Interaction, member: discord.Member, note: str):
        await interaction.response.defer(ephemeral=True)
        await db.record_note(staff_id=interaction.user.id, user_id=member.id, username=member.name, reason=note) #TODO Add error catching here lowk kinda risky atm
        await interaction.followup.send(f"Added a note to {member.mention}")

    @app_commands.guilds(discord.Object(id=DEV_GUILD_ID))
    @app_commands.command(name="get-note", description="Gets a users notes")
    @app_commands.default_permissions(administrator=True)
    async def get_notes(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        notes = await db.get_notes(user_id=member.id)

        await interaction.followup.send(str(notes))
async def setup(bot):
    await bot.add_cog(Moderation(bot))