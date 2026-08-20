import discord
from src.schemas.db_schemas import UserNotes, Ban
import datetime
from src.utils.input_utils import date_to_time, time_between_dates

POSITIVE_COLOR = discord.Color.green()
NEUTRAL_COLOR = discord.Color.gold()
NEGATIVE_COLOR = discord.Color.red()

BRAND_COLOR = discord.Color.orange()

def ui_response_message(contents: str, tone) -> discord.Embed:
    match tone:
        case "positive":
            embed = discord.Embed(color=POSITIVE_COLOR)
        case "neutral":
            embed = discord.Embed(color=NEUTRAL_COLOR)
        case "negative":
            embed = discord.Embed(color=NEGATIVE_COLOR)
        case _:
            embed = discord.Embed()


    embed.set_author(name=contents)

    return embed


def ui_notes_message(notes_package: UserNotes, isWarning: bool = False) -> discord.Embed:
    text = "Notes" if not isWarning else "Warnings"
    embed = discord.Embed(title=f"{text} for {notes_package.username}", color=BRAND_COLOR)

    notes = notes_package.notes
    if notes == []:
        embed.add_field(name=f"No {text}!", value=f"The user has no {text}")
    for note in notes:
        embed.add_field(name=f"{note.content[:245]}", value=f"Note id: {note.note_id} \n Timestamp: {note.timestamp.strftime("%d/%m/%y")} \n Added by: {note.staff_id}", inline=False)

    return embed

def ui_ban_message(guild_name: str, guild_img, reason, unban_date: str) -> discord.Embed:
    
    embed = discord.Embed(title=f"You have been banned from {guild_name} for {date_to_time(unban_date)}", description=f"Ban reason: {reason}")
    embed.set_thumbnail(url=guild_img)
    return embed

def ui_ban_reason(ban: Ban)  -> discord.Embed:
    if ban.ban_date is None or ban.unban_date is None:
        return discord.Embed()

    embed = discord.Embed(
        title=f"Ban for {ban.username}",
        color=BRAND_COLOR,
        description=(
            f"{ban.reason}\n\n"
            f"{time_between_dates(datetime.datetime.now(), ban.unban_date)} until unban ({ban.unban_date})\n"
            f"Originally banned on {ban.ban_date}"
        ),
    )
    embed.set_footer(text=f"Banned by {ban.staff_id}")

    return embed

def ui_dm_message(message_type: str, guild_name: str, guild_img, contents: str=""):
    if contents == "":
        embed = discord.Embed(
                title=f"You have been {message_type} from {guild_name}"
            )

    else:
        embed = discord.Embed(
                title=f"You have been {message_type} from {guild_name}", description=f"Reason: {contents}"
            )

    embed.set_thumbnail(url=guild_img)
    return embed


def ui_edit_message(before: discord.Message, after: discord.Message):
    embed = discord.Embed(
        title="Message Edited",
        description=f"From: {before.author.mention} in {getattr(before.channel, 'mention', str(before.channel.id))}",
        color=NEUTRAL_COLOR
    )

    embed.add_field(name="Before", value=before.content)
    embed.add_field(name="After", value=after.content)

    return embed


def ui_delete_message(message: discord.Message):
    embed = discord.Embed(
        title="Message Deleted",
        description=f"From: {message.author.mention} in {getattr(message.channel, 'mention', str(message.channel.id))}",
        color=NEGATIVE_COLOR
    )

    content_text = message.content if message.content else "No text content"
    embed.add_field(name="Content", value=content_text)

    if message.attachments:
        file_list = "\n".join([f"[{att.filename}]({att.url})" for att in message.attachments])
        embed.add_field(name="Attachments", value=file_list, inline=False)

    return embed