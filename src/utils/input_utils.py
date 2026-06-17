import discord
from discord import app_commands

async def sanitize_inputs(value: str):
    cleaned_input = value.strip("<@!>")

    if cleaned_input.isdigit():
        return int(cleaned_input)
    return cleaned_input