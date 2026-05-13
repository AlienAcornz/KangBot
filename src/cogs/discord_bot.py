import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_DIR = BASE_DIR / ".env"


load_dotenv(ENV_DIR)
token: str = os.getenv('DISCORD_TOKEN', '')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()

intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix="!", intents=intents)

@client.event
async def on_ready():
    if client.user is None:
        print("Bot failed to start - client.user is None")
        return
    print(f"Bot started successfully! {client.user.name}")


@client.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")

client.run(token, log_handler=handler, log_level=logging.DEBUG)