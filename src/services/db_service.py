import datetime
from typing import Optional
from config import POSTGRES_USERNAME, POSTGRES_PASSWORD
from src.schemas.db_schemas import UserNotes, Note, Ban
import os
import asyncpg

class ModDB:
    def __init__(self, dsn):
        self.dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    @property
    def db(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database not connected!")
        return self._pool

    async def connect(self):
        if self._pool is not None:
            raise RuntimeError("Database already connected!")
        
        self._pool = await asyncpg.create_pool(dsn=self.dsn)

        async with self.db.acquire() as conn:

            #ban table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bans (
                    profile_id BIGINT PRIMARY KEY,
                    content TEXT NOT NULL,
                    ban_date TIMESTAMPTZ,
                    unban_date TIMESTAMPTZ,
                    staff_id BIGINT,
                    FOREIGN KEY (profile_id) REFERENCES profiles (profile_id) ON DELETE CASCADE
                )
            ''')

            #notes table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    note_id INTEGER,
                    profile_id BIGINT,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMPTZ,
                    is_warning INTEGER,
                    staff_id BIGINT,
                    PRIMARY KEY (profile_id, note_id),
                    FOREIGN KEY (profile_id) REFERENCES profiles (profile_id) ON DELETE CASCADE
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id BIGINT PRIMARY KEY,
                    log_channel_id BIGINT
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT NOT NULL,
                    guild_id BIGINT
                )
            '''
            )

        print("ModDB connected!")

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def validate_inputs(self, query, guild_id: int) -> int: #THERE IS AN ERROR HERW
        if isinstance(query, int):
            return query

        if isinstance(query, str):
            user_id = await self.get_user_id(username=query, guild_id=guild_id)
            if user_id is None:
                print("COULDNT FIND USER")
                raise ValueError(f"Could not find user: {query} in the database")
            return int(user_id)

        raise ValueError("Please enter a valid type for the user field.")

    async def get_profile_id(self, user_id: int, guild_id: int) -> int:
        query = """
            SELECT profile_id FROM profiles WHERE user_id = $1 AND guild_id = $2
        """

        return await self.db.fetchval(query, user_id, guild_id)

    async def append_user(self, user_id: int, username:str, guild_id: int):
        if not user_id or not username or not guild_id:
            raise TypeError("guild_id, username and user_id are required.")

        query = """
            INSERT INTO profiles (user_id, username, guild_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, guild_id) DO UPDATE SET username = EXCLUDED.username;
        """
        await self.db.execute(query, user_id, username, guild_id)


    async def record_warning(self, staff_id: int, user_id: int, username: str, reason: str, guild_id: int): #records a warning
        await self.record_note(user_id=user_id, reason=reason, is_warning=1, staff_id=staff_id, username=username, guild_id=guild_id)

    
    async def record_note(self, staff_id: int, user_id: int, reason: str, guild_id: int, username: Optional[str] = None, is_warning: int = 0):
        if username:
            await self.append_user(user_id=user_id, username=username, guild_id=guild_id)
        query = """
        INSERT INTO notes (profile_id, note_id, content, timestamp, is_warning, staff_id)
        VALUES (
            $1, 
            (SELECT COALESCE(MAX(note_id), 0) + 1 FROM notes WHERE profile_id = $1), 
            $2, $3, $4, $5
        )
        """
        profile_id = await self.get_profile_id(user_id=user_id,guild_id=guild_id)
        await self.db.execute(
        query,
        profile_id, reason, datetime.datetime.now(datetime.timezone.utc), is_warning, staff_id
        )
    
    async def record_ban(self, staff_id: int, user_id: int,  reason: str, guild_id: int, unban_date: datetime.datetime, username: str):
            await self.append_user(user_id=user_id, username=username, guild_id=guild_id)
            profile_id = await self.get_profile_id(user_id=user_id,guild_id=guild_id)
            await self.db.execute(
                "INSERT INTO bans (profile_id, content, ban_date, unban_date, staff_id, guild_id) VALUES ($1, $2, $3, $4, $5)",
                profile_id, reason, datetime.datetime.now(datetime.timezone.utc), unban_date, staff_id, guild_id
            )


    
    async def get_notes(self, user, guild_id: int, is_warning: int = 0) -> UserNotes:
        user_id = await self.validate_inputs(query=user, guild_id=guild_id)
        query = """
            SELECT profiles.username, notes.staff_id, notes.content, notes.note_id, notes.timestamp
            FROM notes
            INNER JOIN profiles ON notes.profile_id = profiles.profile_id
            WHERE notes.profile_id = $1 AND notes.is_warning = $2
        """

        profile_id = await self.get_profile_id(user_id=user_id, guild_id=guild_id)
        rows = await self.db.fetch(query, profile_id, is_warning)

        if not rows:
            return UserNotes(username="null", notes=[])

        username = str(user_id)
        if rows:
            username = rows[0][0]

        total_notes = []
        for note in rows:
            total_notes.append(Note(staff_id=note[1], content=note[2], note_id=note[3], timestamp=note[4]))
        return UserNotes(username=username, notes=total_notes)


    async def get_warnings(self, user, guild_id: int):
        return await self.get_notes(user=user,guild_id=guild_id,is_warning = 1)
    

    
    async def get_ban_reason(self, user, guild_id: int) -> Ban:

        user_id = await self.validate_inputs(query=user, guild_id=guild_id)
        profile_id = await self.get_profile_id(user_id=user_id,guild_id=guild_id)
        query = "SELECT bans.content, bans.ban_date, bans.unban_date, bans.staff_id, profiles.username FROM bans INNER JOIN profiles ON bans.profile_id = profiles.profile_id WHERE bans.profile_id = $1"
        row = await self.db.fetchrow(query, profile_id)
        if not row:
            return Ban(reason="", ban_date=datetime.datetime.now(datetime.timezone.utc), unban_date=datetime.datetime.now(datetime.timezone.utc), staff_id=0, username="null")

        print(row)
        return Ban(reason=row["content"], ban_date=row["ban_date"], unban_date=row["unban_date"], staff_id=row["staff_id"], username=row["username"])

        


    
    async def revoke_ban(self, user, guild_id: int, silent: bool = False) -> int:
        user_id: int = await self.validate_inputs(query=user, guild_id=guild_id)
        profile_id = await self.get_profile_id(user_id=user_id,guild_id=guild_id)
        ban_reason = ban_reason = await self.db.fetchval(
            "SELECT content FROM bans WHERE profile_id = $1", 
            profile_id
        )

        if ban_reason is None:
            return 0
        await self.db.execute("DELETE FROM bans WHERE profile_id = $1", profile_id)

        if silent == False:
             await self.record_note(user_id=user_id,reason=f"User was previously banned with the reason: {ban_reason["content"]}", staff_id=0, guild_id=guild_id) #NOTE STAFF ID SET TO 0. THIS SHOULD PROBABLY CHANGE IN THE FUTURE
        
        
        return user_id

    async def revoke_warning(self, user, warning_id: int, guild_id: int):
        await self.revoke_note(user, warning_id, guild_id)


    
    async def revoke_note(self, user, note_id: int, guild_id: int):
        user_id = await self.validate_inputs(query=user, guild_id=guild_id)
        profile_id = await self.get_profile_id(user_id=user_id, guild_id=guild_id)
    
        command_tag = await self.db.execute(
            "DELETE FROM notes WHERE profile_id = $1 AND note_id = $2",
            profile_id,
            note_id,
        )

        deleted_rows = int(command_tag.split()[-1]) if command_tag else 0
        success = deleted_rows > 0
        return success



    async def clean_users(self): #deletes all users that do not have a note or a ban from the database
        if self.db is None:
            raise RuntimeError("Database not connected!")

        await self.db.execute("""
        DELETE FROM profiles
        WHERE NOT EXISTS (SELECT 1 FROM notes WHERE notes.profile_id = profiles.profile_id)
        AND NOT EXISTS (SELECT 1 FROM bans WHERE bans.profile_id = profiles.profile_id)
        """)


    async def get_unbanned_users(self):
        rows = await self.db.fetch("SELECT user_id, guild_id FROM bans WHERE unban_date < $1", datetime.datetime.now(datetime.timezone.utc))

        guild_map = {}

        for user_id, guild_id in rows:
            guild_map.setdefault(guild_id, []).append(user_id)

        return guild_map
    

        
    async def get_user_id(self, username: str, guild_id: int):
        return await self.db.fetchval("SELECT user_id FROM profiles WHERE username = $1 AND guild_id = $2", username, guild_id)

    async def get_username(self, user_id: int, guild_id: int):
        return await self.db.fetchval("SELECT username FROM profiles WHERE user_id = $1 AND guild_id = $2", user_id, guild_id)

    async def set_log_channel(self, guild_id: int, channel_id: int):
        query = """
                INSERT INTO guilds (guild_id, log_channel_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET log_channel_id = EXCLUDED.log_channel_id;
                """
        await self.db.execute(
            query,
            guild_id, channel_id
        )

    async def get_log_channel(self, guild_id: int):
        return await self.db.fetchval("SELECT log_channel_id FROM guilds WHERE guild_id = $1", guild_id)
    
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")  # falls back to localhost for local dev
db = ModDB(dsn=f"postgresql://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/moderation")