import discord
from discord.ext import commands
from discord import app_commands
from functools import wraps
from src.services.db_service import db
from src.utils.db_utils import run_with_timeout
from src.utils.input_utils import sanitize_inputs
import asyncio

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
        await interaction.response.send_message(f"{member.mention} softbanned!")

    


    @app_commands.command(name="add-note", description="Adds a note to a user")
    @app_commands.default_permissions(administrator=True)
    async def add_note_command(self, interaction: discord.Interaction, member: discord.Member, note: str):
        await interaction.response.defer(ephemeral=True)
        success, result = await run_with_timeout(db.record_note(staff_id=interaction.user.id, user_id=member.id, username=member.name, reason=note))

        if not success:
            if isinstance(result, asyncio.TimeoutError):
                await interaction.followup.send("The command timed out!")
            else:
                await interaction.followup.send("There was an error performing the command!")
        await interaction.followup.send(f"Added a note to {member.mention}")



    @app_commands.command(name="get-notes", description="Gets a users notes")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(input=autocomplete)
    async def get_notes_command(self, interaction: discord.Interaction, input: str):
        await interaction.response.defer(ephemeral=True)
        target = await sanitize_inputs(input)


        success, notes_package = await run_with_timeout(db.get_notes(user=target))

        if not success:
            if isinstance(notes_package, asyncio.TimeoutError):
                await interaction.followup.send("The command timed out!")
                return False
            else:
                await interaction.followup.send("There was an error performing the command!")
                return False

        if notes_package.username == "null":
            #USER NOT FOUND TODO
            pass

        embed = discord.Embed(title=f"Notes for {notes_package.username}")

        notes = notes_package.notes
        if notes == []:
            embed.add_field(name="No notes!", value="The user has no notes")
        for note in notes:
            embed.add_field(name=note.content, value=f"Added by: {note.staff_id}", inline=False)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))