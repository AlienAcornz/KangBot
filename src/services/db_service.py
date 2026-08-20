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

        #user table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT NOT NULL
                )
            ''')

            #ban table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bans (
                    user_id BIGINT,
                    content TEXT NOT NULL,
                    ban_date TIMESTAMPTZ,
                    unban_date TIMESTAMPTZ,
                    staff_id BIGINT,
                    guild_id BIGINT,
                    PRIMARY KEY (user_id, guild_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            #notes table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    note_id INTEGER,
                    user_id BIGINT,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMPTZ,
                    is_warning INTEGER,
                    staff_id BIGINT,
                    guild_id BIGINT,
                    PRIMARY KEY (user_id, guild_id, note_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id BIGINT PRIMARY KEY,
                    log_channel_id BIGINT
                )
            ''')

        print("ModDB connected!")

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def validate_inputs(self, query) -> int: #THERE IS AN ERROR HERW
        if isinstance(query, int):
            return query

        if isinstance(query, str):
            user_id = await self.get_user_id(query)
            if user_id is None:
                print("COULDNT FIND USER")
                raise ValueError(f"Could not find user: {query} in the database")
            return int(user_id)

        raise ValueError("Please enter a valid type for the user field.")


    async def append_user(self, user_id: int, username:str):
        if not user_id or not username:
            raise TypeError("Both username and user_id are required.")

        query = """
            INSERT INTO users (user_id, username)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username;
        """
        await self.db.execute(query, user_id, username)


    async def record_warning(self, staff_id: int, user_id: int, username: str, reason: str, guild_id: int): #records a warning
        await self.record_note(user_id=user_id, reason=reason, is_warning=1, staff_id=staff_id, username=username, guild_id=guild_id)

    
    async def record_note(self, staff_id: int, user_id: int, reason: str, guild_id: int, username: Optional[str] = None, is_warning: int = 0):
        if username:
            await self.append_user(user_id=user_id, username=username)
        query = """
        INSERT INTO notes (user_id, note_id, content, timestamp, is_warning, staff_id, guild_id)
        VALUES (
            $1, 
            (SELECT COALESCE(MAX(note_id), 0) + 1 FROM notes WHERE user_id = $2 AND guild_id = $3), 
            $4, $5, $6, $7, $8
        )
        """
        await self.db.execute(
        query,
        user_id, user_id, guild_id, reason, datetime.datetime.now(datetime.timezone.utc), is_warning, staff_id, guild_id
        )
    
    async def record_ban(self, staff_id: int, user_id: int,  reason: str, guild_id: int, unban_date: datetime.datetime, username: str):
            await self.append_user(user_id=user_id, username=username)

            await self.db.execute(
                "INSERT INTO bans (user_id, content, ban_date, unban_date, staff_id, guild_id) VALUES ($1, $2, $3, $4, $5, $6)",
                user_id, reason, datetime.datetime.now(datetime.timezone.utc), unban_date, staff_id, guild_id
            )


    
    async def get_notes(self, user, guild_id: int, is_warning: int = 0) -> UserNotes:
        user_id = await self.validate_inputs(user)
        query = """
            SELECT users.username, notes.staff_id, notes.content, notes.note_id, notes.timestamp
            FROM notes
            INNER JOIN users ON notes.user_id = users.user_id
            WHERE notes.user_id = $1 AND notes.is_warning = $2 AND notes.guild_id = $3
        """
        rows = await self.db.fetch(query, user_id, is_warning, guild_id)

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

        user_id = await self.validate_inputs(user)
        query = "SELECT bans.content, bans.ban_date, bans.unban_date, bans.staff_id, users.username FROM bans INNER JOIN users ON bans.user_id = users.user_id WHERE bans.user_id = $1 AND bans.guild_id = $2"
        row = await self.db.fetchrow(query, user_id,guild_id)
        if not row:
            return Ban(reason="", ban_date=datetime.datetime.now(datetime.timezone.utc), unban_date=datetime.datetime.now(datetime.timezone.utc), staff_id=0, username="null")

        print(row)
        return Ban(reason=row["content"], ban_date=row["ban_date"], unban_date=row["unban_date"], staff_id=row["staff_id"], username=row["username"])

        


    
    async def revoke_ban(self, user, guild_id: int, silent: bool = False) -> int:
        user_id: int = await self.validate_inputs(user)

        ban_reason = ban_reason = await self.db.fetchval(
            "SELECT content FROM bans WHERE user_id = $1 AND guild_id = $2", 
            user_id, guild_id
        )

        if ban_reason is None:
            return 0
        await self.db.execute("DELETE FROM bans WHERE user_id = $1 AND guild_id = $2", user_id,guild_id)

        if silent == False:
             await self.record_note(user_id=user_id,reason=f"User was previously banned with the reason: {ban_reason["content"]}", staff_id=0, guild_id=guild_id) #NOTE STAFF ID SET TO 0. THIS SHOULD PROBABLY CHANGE IN THE FUTURE
        
        
        return user_id

    async def revoke_warning(self, user, warning_id: int, guild_id: int):
        await self.revoke_note(user, warning_id, guild_id)


    
    async def revoke_note(self, user, note_id: int, guild_id: int):
        user_id = await self.validate_inputs(user)
    
        command_tag = await self.db.execute(
            "DELETE FROM notes WHERE user_id = $1 AND note_id = $2 AND guild_id = $3",
            user_id,
            note_id,
            guild_id,
        )

        deleted_rows = int(command_tag.split()[-1]) if command_tag else 0
        success = deleted_rows > 0
        return success



    async def clean_users(self): #deletes all users that do not have a note or a ban from the database
        if self.db is None:
            raise RuntimeError("Database not connected!")

        await self.db.execute("""
        DELETE FROM users
        WHERE NOT EXISTS (SELECT 1 FROM notes WHERE notes.user_id = users.user_id)
        AND NOT EXISTS (SELECT 1 FROM bans WHERE bans.user_id = users.user_id)
        """)


    async def get_unbanned_users(self):
        rows = await self.db.fetch("SELECT user_id, guild_id FROM bans WHERE unban_date < $1", datetime.datetime.now(datetime.timezone.utc))

        guild_map = {}

        for user_id, guild_id in rows:
            guild_map.setdefault(guild_id, []).append(user_id)

        return guild_map
    

        
    async def get_user_id(self, username: str):
        return await self.db.fetchval("SELECT user_id FROM users WHERE username = $1", username)

    async def get_username(self, user_id: int):
        return await self.db.fetchval("SELECT username FROM users WHERE user_id = $1", user_id)

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