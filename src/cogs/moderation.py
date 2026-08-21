import discord
from discord.ext import commands
from discord import app_commands
from functools import wraps
from src.services.db_service import db
from src.utils.db_utils import run_with_timeout
from src.utils.input_utils import sanitize_inputs, str_to_time, date_to_time
import asyncio
from src.utils.bot_ui import ui_response_message, ui_notes_message, ui_ban_message,ui_ban_reason, ui_dm_message
import datetime

def check_role_hierarchy(func):
    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, member: discord.Member, *args, **kwargs):

        if interaction.user == member: #If the person running the command is the same as the target user
            await interaction.response.send_message(embed=ui_response_message(contents="❌ You cannot moderate yourself!", tone="negative"),ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member) or interaction.guild is None:
            await interaction.response.send_message(embed=ui_response_message(contents="❌This command must be used in a server where role hierarchy is available.", tone="negative"),ephemeral=True)
            return

        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=ui_response_message(contents="❌You cannot moderate a member with a role equal to or higher than yours!", tone="negative"),
                ephemeral=True
            )
            return
        

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                embed=ui_response_message(contents="❌ I cannot moderate a member with a role equal to or higher than my top role!", tone="negative"),
                ephemeral=True
            )
            return
        
        return await func(self, interaction, member, *args, **kwargs)
    return wrapper

def check_guild_present(func):
    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, member: discord.Member, *args, **kwargs):
        if not interaction.guild:
            await interaction.followup.send(embed=ui_response_message(contents="❌ You must run the command inside a guild!", tone="negative"))
            return
        
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
    @check_guild_present
    @check_role_hierarchy
    @app_commands.default_permissions(administrator=True)
    async def kick_command(self, interaction: discord.Interaction, member: discord.Member, reason: str = ""):
        assert interaction.guild is not None
        await member.kick(reason=reason)

        try:
            guild_icon_url = interaction.guild.icon.url if interaction.guild.icon else None
            await member.send(embed=ui_dm_message(guild_name=interaction.guild.name,guild_img=guild_icon_url, message_type="kicked", contents=reason))
        except discord.Forbidden:
            pass
        ostream = f"Kicked {member.mention} for: {reason}" if reason != "" else f"Kicked {member.mention}" #TODO Create fancy embed here
        await interaction.response.send_message(ostream)



    @app_commands.command(name="softban", description="Temporarily bans and then unbans a user")
    @check_guild_present
    @check_role_hierarchy
    @app_commands.default_permissions(administrator=True)
    async def softban_command(self, interaction: discord.Interaction, member: discord.Member, reason: str = ""):
        assert interaction.guild is not None

        await member.ban(reason=reason)
        await interaction.guild.unban(member)
        await interaction.response.send_message(embed=ui_response_message(f"✅ Softbanned {member.name}", tone="positive"), ephemeral=True)
        await member.send(embed=ui_response_message(f"❌ You were kicked from {interaction.guild.name}", tone="negative"))


    #====NOTES====


    @app_commands.command(name="add-note", description="Adds a note to a user")
    @check_guild_present
    @app_commands.default_permissions(administrator=True)
    async def add_note_command(self, interaction: discord.Interaction, member: discord.Member, note: app_commands.Range[str, 1, 245]):
        await interaction.response.defer(ephemeral=True)
        assert interaction.guild is not None

        success, result = await run_with_timeout(db.record_note(staff_id=interaction.user.id, user_id=member.id, username=member.name, reason=note, guild_id=interaction.guild.id))


        if not success:
            if isinstance(result, asyncio.TimeoutError):
                await interaction.followup.send(embed=ui_response_message(contents="⌛ The action timed out",tone="negative"))
            else:
                await interaction.followup.send(embed=ui_response_message(contents="❌ An error occured", tone="negative"))
        await interaction.followup.send(embed=ui_response_message(contents=f"✅ Added a note to {member.name}", tone="positive"))


    @app_commands.command(name="get-notes", description="Gets a users notes")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(query=autocomplete)
    async def get_notes_command(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        target = sanitize_inputs(query)

        if interaction.guild_id:
            _, notes_package = await run_with_timeout(db.get_notes(user=target, guild_id=interaction.guild_id))
        else:
            await interaction.followup.send(embed=ui_response_message("❌ This command must be ran within a guild", tone="negative"))

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


    @app_commands.command(name="delete-note", description="Deletes a users note")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(query=autocomplete)
    async def revoke_note_command(self, interaction: discord.Interaction, query: str, note_id: int):
        await interaction.response.defer(ephemeral=True)
        target = sanitize_inputs(query)

        if interaction.guild_id:
            success = await db.revoke_note(user=target, note_id=note_id, guild_id=interaction.guild_id)
        else:
            await interaction.followup.send(embed=ui_response_message("❌ This command must be ran within a guild!", tone="negative"))
        if not success:
            await interaction.followup.send(embed=ui_response_message("❌Could not find the user or note id", tone="negative"))
            return
        
        await interaction.followup.send(embed=ui_response_message("✅Note successfully removed", tone="positive"))


    #====WARNINGS====


    @app_commands.command(name="add-warning", description="Adds a warning to a user")
    @check_guild_present
    @app_commands.default_permissions(administrator=True)
    @check_role_hierarchy
    async def add_warning_command(self, interaction: discord.Interaction, member: discord.Member, warning: app_commands.Range[str, 1, 245]):
        await interaction.response.defer(ephemeral=True)
        assert interaction.guild is not None
        success, result = await run_with_timeout(db.record_warning(staff_id=interaction.user.id, user_id=member.id, username=member.name, reason=warning, guild_id=interaction.guild.id))



        if not success:
            if isinstance(result, asyncio.TimeoutError):
                await interaction.followup.send(embed=ui_response_message(contents="⌛ The action timed out",tone="negative"))
                return
            else:
                await interaction.followup.send(embed=ui_response_message(contents="❌ An error occured", tone="negative"))
                return

        try:
            guild_icon_url = interaction.guild.icon.url if interaction.guild.icon else None
            await member.send(embed=ui_dm_message(guild_name=interaction.guild.name,guild_img=guild_icon_url, message_type="warned", contents=warning))
        except discord.Forbidden:
            pass

        await interaction.followup.send(embed=ui_response_message(contents=f"✅ Added a warning to {member.name}", tone="positive"))


    @app_commands.command(name="get-warnings", description="Gets a users warnings")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(query=autocomplete)
    async def get_warnings_command(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        target = sanitize_inputs(query)

        if interaction.guild_id:
            _, notes_package = await run_with_timeout(db.get_warnings(user=target, guild_id=interaction.guild_id))
        else:
            await interaction.followup.send(embed=ui_response_message("❌ This command must be ran within a guild!", tone="negative"))

        if isinstance(notes_package, Exception):
            if isinstance(notes_package, asyncio.TimeoutError):
                await interaction.followup.send(embed=ui_response_message("⌛ The command timed out!", tone="neutral"))
            else:
                await interaction.followup.send(embed=ui_response_message("❌ There was an error performing the command", tone="negative"))
            return

        if notes_package.username == "null":
            await interaction.followup.send(embed=ui_response_message("❌ Could not find the target!", tone="negative"))
            return False

        await interaction.followup.send(embed=ui_notes_message(notes_package, isWarning=True))


    @app_commands.command(name="delete-warning", description="Deletes a users warning")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(query=autocomplete)
    async def revoke_warning_command(self, interaction: discord.Interaction, query: str, warning_id: int):
        await interaction.response.defer(ephemeral=True)
        target = sanitize_inputs(query)

        if interaction.guild_id:
            success = await db.revoke_warning(user=target, warning_id=warning_id, guild_id=interaction.guild_id)
        else:
            await interaction.followup.send(embed=ui_response_message("❌ This command must be ran within a guild!", tone="negative"))
            return
        if not success:
            await interaction.followup.send(embed=ui_response_message("❌ Could not find the user or note id", tone="negative"))
            return
        
        await interaction.followup.send(embed=ui_response_message("✅ Warning successfully removed", tone="positive"))


    #===BANS====

    @app_commands.command(name="ban", description="Bans a user.")
    @check_guild_present
    @app_commands.default_permissions(administrator=True)
    @check_role_hierarchy
    @app_commands.describe(
        duration="Format: m,h,d,w,y being minute,hour,day,week,year"
    )
    async def add_ban_command(self, interaction: discord.Interaction, member: discord.Member, reason: app_commands.Range[str, 1, 245], duration: str):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        time = str_to_time(duration)
        if isinstance(time, bool):
            await interaction.followup.send(embed=ui_response_message(contents="❌ Invalid unban date", tone="negative"))
            return
        
        success, result = await run_with_timeout(db.record_ban(staff_id=interaction.user.id, user_id=member.id, username=member.name, reason=reason, unban_date=time, guild_id=interaction.guild.id))

        if not success:
            if isinstance(result, asyncio.TimeoutError):
                await interaction.followup.send(embed=ui_response_message(contents="⌛ The action timed out",tone="negative"))
                return
            else:
                await interaction.followup.send(embed=ui_response_message(contents="❌ An error occured", tone="negative"))
                return
            
        try:
            guild_icon_url = interaction.guild.icon.url if interaction.guild.icon else None
            await member.send(embed=ui_ban_message(guild_name=interaction.guild.name,guild_img=guild_icon_url, reason=reason, unban_date=duration))
        except discord.Forbidden:
            pass

        await member.ban(reason=reason)
        await interaction.followup.send(embed=ui_response_message(contents=f"✅ Banned {member.name} for {date_to_time(duration)}", tone="positive"))


    
    @app_commands.command(name="get-ban-reason", description="Retrieves the reason a user was banned")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(query=autocomplete)
    async def get_ban_command(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        target = sanitize_inputs(query)

        print(f"Target: {target}")
        if interaction.guild_id:
            _, ban = await run_with_timeout(db.get_ban_reason(user=target, guild_id=interaction.guild_id))
        else:
            await interaction.followup.send(embed=ui_response_message("❌ This command must be ran within a guild!", tone="negative"))
            return

        if isinstance(ban, Exception):
            if isinstance(ban, asyncio.TimeoutError):
                await interaction.followup.send(embed=ui_response_message("⌛ The command timed out!", tone="neutral"))
            else:
                await interaction.followup.send(embed=ui_response_message("❌ There was an error performing the command", tone="negative"))
            return

        if ban.username == "null":
            await interaction.followup.send(embed=ui_response_message("❌ Could not find the target!", tone="negative"))
            return False

        print(f"ban reason: {ban.reason}")
        await interaction.followup.send(embed=ui_ban_reason(ban=ban))

    

    @app_commands.command(name="revoke-ban", description="Revokes a ban")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(query=autocomplete)
    async def revoke_ban_command(self, interaction: discord.Interaction, query: str, silent: bool=False):
        await interaction.response.defer(ephemeral=True)
        target = sanitize_inputs(query)

        if interaction.guild:
            _, user_id = await run_with_timeout(db.revoke_ban(user=target, silent=silent, guild_id=interaction.guild.id))
        else:
            await interaction.followup.send(embed=ui_response_message(contents="❌ You must run the command inside a guild!", tone="negative"))
            return


        if isinstance(user_id, Exception):
            if isinstance(user_id, asyncio.TimeoutError):
                await interaction.followup.send(embed=ui_response_message("⌛ The command timed out!", tone="neutral"))
            else:
                await interaction.followup.send(embed=ui_response_message("❌ There was an error performing the command", tone="negative"))
            return

        if user_id == 0:
            await interaction.followup.send(embed=ui_response_message("❌ Could not find the target!", tone="negative"))
            return False
        
        if interaction.guild:
            await interaction.guild.unban(user=discord.Object(id=user_id))
        else:
            await interaction.followup.send(embed=ui_response_message("❌ There was an error performing the command", tone="negative"))
        
        username = await db.get_username(user_id=user_id, guild_id=interaction.guild.id)

        await interaction.followup.send(embed=ui_response_message(f"✅ {username} unbanned!", tone="positive"))



    @app_commands.command(name="set-logs", description="Defines current channel as logs")
    @app_commands.default_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction):
        if not interaction.guild or not interaction.channel:
            return
        await interaction.response.defer(ephemeral=True)
        await db.set_log_channel(guild_id=interaction.guild.id, channel_id=interaction.channel.id)

        await interaction.followup.send(embed=ui_response_message(f"✅ Set {getattr(interaction.channel, 'mention', str(interaction.channel.id))} as the log channel!", tone="positive"))
async def setup(bot):
    await bot.add_cog(Moderation(bot))