import asyncio
import aiosqlite
import datetime
from typing import Optional
from functools import wraps

DB_PATH = "moderation.db"


def resolve_user(func):
     @wraps(func)

     async def wrapper(self, user_id: Optional[int] = None, username: Optional[str] = None, *args, **kwargs):
        if user_id is None and username is None:
            raise ValueError("Either user_id or username must be provided")
        
        if username is not None and user_id is None:
            user_id = await self.get_user_id(username)

            is_creation_func = func.__name__ in ("record_note", "record_ban", "record_warning")

            if user_id is None and not is_creation_func:
                raise ValueError(f"User '{username}' not found")
        
        return await func(self, user_id=user_id, username=username, *args, **kwargs)
     
     return wrapper

class ModDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    @property
    def db(self):
        if self._db is None:
            raise RuntimeError("Database not connected!")
        return self._db

    async def connect(self):
        if self._db is not None:
            raise RuntimeError("Database already connected!")
        
        self._db = await aiosqlite.connect(self.db_path)
        await self.db.execute("PRAGMA foreign_keys = ON")

        #user table
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL
            )
        ''')

        #ban table
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS bans (
                ban_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT NOT NULL,
                ban_date DATETIME,
                unban_date DATETIME,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        #notes table
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT NOT NULL,
                timestamp DATETIME,
                is_warning INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        await self.db.commit()

        print("ModDB connected!")

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def append_user(self, user_id: Optional[int], username: Optional[str] = None):
            cursor = await self.db.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = ?)", (user_id,))
            result = await cursor.fetchone()
            user_exists =  bool(result[0]) if result else False

            if not user_exists:
                if username == None or user_id == None:
                    raise TypeError("Both username and user id field required as user does not already exist.")

                await self.db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id,username))
                await self.db.commit()


    async def record_warning(self, user_id: Optional[int], reason: str, username: Optional[str]=None): #records a warning
        await self.record_note(user_id=user_id, reason=reason, is_warning=1, username=username)

    @resolve_user
    async def record_note(self, user_id: Optional[int], reason: str, username: Optional[str]=None, is_warning: int = 0):
        await self.append_user(user_id=user_id, username=username)

        await self.db.execute(
            "INSERT INTO notes (user_id, content, timestamp, is_warning) VALUES (?, ?, ?, ?)",
            (user_id, reason, datetime.datetime.now(), is_warning)
        )
        await self.db.commit()

    @resolve_user
    async def record_ban(self, user_id: Optional[int],  reason: str, unban_date: datetime.datetime, username: Optional[str] = None):
            await self.append_user(user_id=user_id, username=username)

            await self.db.execute(
                "INSERT INTO bans (user_id, content, ban_date, unban_date) VALUES (?, ?, ?, ?)",
                (user_id, reason, datetime.datetime.now(), unban_date)
            )
            await self.db.commit()


    @resolve_user
    async def get_notes(self, user_id: Optional[int], isWarning: int = 0):
        cursor = await self.db.execute("SELECT  note_id, content FROM notes WHERE user_id = ? AND is_warning = ?", (user_id,isWarning))
        rows = await cursor.fetchall()
        return [(row[0], row[1]) for row in rows]


    async def get_warnings(self, user_id: Optional[int]):
        return await self.get_notes(user_id,isWarning = 1)
    

    @resolve_user
    async def get_ban_reason(self, user_id: Optional[int]):
        if self.db is None:
            raise RuntimeError("Database not connected!")

        cursor = await self.db.execute("SELECT content FROM bans WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None


    @resolve_user
    async def revoke_ban(self, user_id: Optional[int], silent: bool = False):
        if self.db is None:
            raise RuntimeError("Database not connected!")

        cursor = await self.db.execute("SELECT content FROM bans WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        ban_reason = row[0] if row else None

        await self.db.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))

        await self.db.commit()

        if silent == False:
             await self.record_note(user_id=user_id,reason=f"User was previously banned with the reason: {ban_reason}")


    async def revoke_warning(self, user_id: Optional[int], warning_id: int):
        await self.revoke_note(user_id, warning_id)


    @resolve_user
    async def revoke_note(self, user_id: Optional[int], note_id: int):
        if self.db is None:
            raise RuntimeError("Database not connected!")
    
        await self.db.execute("DELETE FROM notes WHERE user_id = ? AND note_id = ?", (user_id,note_id))

        await self.db.commit()


    async def clean_users(self): #deletes all users that do not have a note or a ban from the database
        if self.db is None:
            raise RuntimeError("Database not connected!")

        await self.db.execute("""
        DELETE FROM users
        WHERE NOT EXISTS (SELECT 1 FROM notes WHERE notes.user_id = users.user_id)
        AND NOT EXISTS (SELECT 1 FROM bans WHERE bans.user_id = users.user_id)
        """)
        await self.db.commit()


    async def get_unbanned_users(self):
        cursor = await self.db.execute("SELECT user_id FROM bans WHERE unban_date < ?", (datetime.datetime.now(),))
        return [row[0] for row in await cursor.fetchall()]
    
    async def get_user_id(self, username: str):
        cursor = await self.db.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        row = await cursor.fetchone()

        return row[0] if row else None