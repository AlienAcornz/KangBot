import discord
from discord.ext import commands, tasks
from src.services.db_service import db

class Events(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

        self.unban_users_event.start()

    @tasks.loop(minutes=1)
    async def unban_users_event(self):
        await self.bot.wait_until_ready()
        unban_guild = await db.get_unbanned_users()

        for guild_id, user_id_list in unban_guild.items():
            print("Guild:", guild_id, "ids:", user_id_list)
            guild = self.bot.get_guild(guild_id)

            if not guild:
                continue

            for user_id in user_id_list:
                user = discord.Object(id=user_id)

                try:
                    await db.revoke_ban(user=user_id, guild_id=guild_id)
                    await guild.unban(user)
                except discord.Forbidden:
                    print(f"Missing permissions to unban {user_id} in guild {guild_id}")
                except discord.HTTPException as e:
                    print(f"Failed to unban {user_id}: {e}")


async def setup(bot):
    await bot.add_cog(Events(bot))

