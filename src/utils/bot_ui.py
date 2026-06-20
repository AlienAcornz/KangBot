import discord
from src.schemas.db_schemas import UserNotes
import datetime

def ui_response_message(contents: str, tone):
    match tone:
        case "positive":
            embed = discord.Embed(color=discord.Color.green())
        case "neutral":
            embed = discord.Embed(color=discord.Color.gold())
        case "negative":
            embed = discord.Embed(color=discord.Color.red())
        case _:
            embed = discord.Embed()


    embed.set_author(name=contents)

    return embed


def ui_notes_message(notes_package: UserNotes, isWarning: bool = False):
    text = "Notes" if not isWarning else "Warnings"
    embed = discord.Embed(title=f"{text} for {notes_package.username}")

    notes = notes_package.notes
    if notes == []:
        embed.add_field(name=f"No {text}!", value=f"The user has no {text}")
    for note in notes:
        embed.add_field(name=f"{note.content[:245]}", value=f"Note id: {note.note_id} \n Timestamp: {note.timestamp.strftime("%d/%m/%y")} \n Added by: {note.staff_id}", inline=False)

    return embed