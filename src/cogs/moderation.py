import discord
from discord.ext import commands
from discord import app_commands
from functools import wraps
from src.services.db_service import db
from src.utils.db_utils import run_with_timeout
from src.utils.input_utils import sanitize_inputs
import asyncio
from src.utils.bot_ui import ui_response_message, ui_notes_message

def check_role_hierarchy(func):
    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, member: discord.Member, *args, **kwargs):

        if interaction.user == member: #If the person running the command is the same as the target user
            await interaction.response.send_message(embed=ui_response_message(contents="❌ You cannot moderate yourself!", tone="negative"),ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(embed=ui_response_message(contents="❌This command must be used in a server where role hierarchy is available.", tone="negative"),ephemeral=True)
            return

        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=ui_response_message(contents="❌You cannot moderate a member with a role equal to or higher than yours!", tone="negative"),
                ephemeral=True
            )
            return
        
        #TODO Check if the bot has a lower role than the target
        
        return await func(self, interaction, member, *args, **kwargs)
    return wrapper

class Moderation(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def autocomplete(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        choices = []
        if not interaction.guild: #If command being ran as a DM return []
            return []
        
        current_lower = current.lower()
        for member in interaction.guild.members:
            if current_lower in member.name.lower() or (member.nick and current_lower in member.nick.lower()): #If the guild member has a name or a nickname that contains the content field, display the user.
                choices.append(
                    app_commands.Choice(
                        name=f"{member.display_name} (@{member.name})", 
                        value=str(member.id)
                    )
                )
            if len(choices) >= 25:
                break
                    
        return choices

    @app_commands.command(name="kick", description="Kicks a user")
    @check_role_hierarchy
    @app_commands.default_permissions(administrator=True)
    async def kick_command(self, interaction: discord.Interaction, member: discord.Member, reason: str = ""):
        await member.kick(reason=reason)
        ostream = f"Kicked {member.mention} for: {reason}" if reason != "" else f"Kicked {member.mention}"
        await interaction.response.send_message(ostream)



    @app_commands.command(name="softban", description="Temporarily bans and then unbans a user")
    @check_role_hierarchy
    @app_commands.default_permissions(administrator=True)
    async def softban_command(self, interaction: discord.Interaction, member: discord.Member, reason: str = ""):
        await member.ban(reason=reason)
        await member.unban(reason=reason)
        await interaction.response.send_message(embed=ui_response_message(f"✅ Softbanned {member.name}", tone="positive"), ephemeral=True)



    @app_commands.command(name="add-note", description="Adds a note to a user")
    @app_commands.default_permissions(administrator=True)
    async def add_note_command(self, interaction: discord.Interaction, member: discord.Member, note: app_commands.Range[str, 1, 245]):
        await interaction.response.defer(ephemeral=True)
        success, result = await run_with_timeout(db.record_note(staff_id=interaction.user.id, user_id=member.id, username=member.name, reason=note))

        if not success:
            if isinstance(result, asyncio.TimeoutError):
                await interaction.followup.send(embed=ui_response_message(contents="⌛The action timed out",tone="negative"))
            else:
                await interaction.followup.send(embed=ui_response_message(contents="❌An error occured", tone="negative"))
        await interaction.followup.send(embed=ui_response_message(contents=f"✅Added a note to {member.name}", tone="positive"))


    @app_commands.command(name="get-notes", description="Gets a users notes")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(query=autocomplete)
    async def get_notes_command(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        target = await sanitize_inputs(query)


        _, notes_package = await run_with_timeout(db.get_notes(user=target))

        if isinstance(notes_package, Exception):
            if isinstance(notes_package, asyncio.TimeoutError):
                await interaction.followup.send(embed=ui_response_message("⌛ The command timed out!", tone="neutral"))
            else:
                await interaction.followup.send(embed=ui_response_message("❌ There was an error performing the command", tone="negative"))
            return

        if notes_package.username == "null":
            await interaction.followup.send(embed=ui_response_message("❌ Could not find the target!", tone="negative"))
            return False

        await interaction.followup.send(embed=ui_notes_message(notes_package))


    @app_commands.command(name="delete-note", description="Gets a users notes")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(query=autocomplete)
    async def revoke_note_command(self, interaction: discord.Interaction, query: str, note_id: int):
        await interaction.response.defer(ephemeral=True)
        target = await sanitize_inputs(query)

        success = await db.revoke_note(user=target, note_id=note_id)
        if not success:
            await interaction.followup.send(embed=ui_response_message("❌Could not find the user or note id", tone="negative"))
            return
        
        await interaction.followup.send(embed=ui_response_message("✅Note successfully removed", tone="positive"))

async def setup(bot):
    await bot.add_cog(Moderation(bot))