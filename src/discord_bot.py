import discord
from discord.ext import commands
from discord import app_commands
import logging
from config import TOKEN,BUILD_TYPE, DEV_GUILD_ID
import os

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True 
        intents.message_content = True
        intents.moderation = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        base = os.path.dirname(__file__) # path to src/
        cogs_dir = os.path.join(base, "cogs") # path to src/cogs/

        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                await self.load_extension(f"src.cogs.{filename[:-3]}")
                print(f"Loaded extension: src.cogs.{filename[:-3]}")
        
        if BUILD_TYPE == "RELEASE":
            await self.tree.sync()
        elif BUILD_TYPE == "DEV":
            #self.tree.clear_commands(guild=None)
            #await self.tree.sync()

            GUILD = discord.Object(id=int(DEV_GUILD_ID))
            self.tree.copy_global_to(guild=GUILD)
            await self.tree.sync(guild=GUILD)
        else:
            raise ValueError("Invalid build type used in .env")

    async def on_ready(self):
        print(f"Logged in as {self.user}")

bot = Bot()
bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)