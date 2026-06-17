import asyncio
import aiosqlite
import datetime
from typing import Optional
from functools import wraps
from config import DB_PATH
from src.schemas.db_schemas import UserNotes, Note

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
                staff_id INTEGER,
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
                staff_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        await self.db.commit()

        print("ModDB connected!")

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def validate_inputs(self, input) -> int:
        if isinstance(input, int):
            return input

        if isinstance(input, str):
            user_id = await self.get_user_id(input)
            if user_id is None:
                print("COULDNT FIND USER")
                raise ValueError(f"Could not find user: {input} in the database")
            return int(user_id)

        raise ValueError("Please enter a valid type for the user field.")


    async def append_user(self, user_id: Optional[int], username: Optional[str] = None):
            cursor = await self.db.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = ?)", (user_id,))
            result = await cursor.fetchone()
            user_exists =  bool(result[0]) if result else False

            if not user_exists:
                if username == None or user_id == None:
                    raise TypeError("Both username and user id field required as user does not already exist.")

                await self.db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id,username))
                await self.db.commit()


    async def record_warning(self, staff_id: int, user_id: Optional[int], reason: str, username: Optional[str]=None): #records a warning
        await self.record_note(user_id=user_id, reason=reason, is_warning=1, username=username, staff_id=staff_id)

    
    async def record_note(self, staff_id: int, user_id: Optional[int], reason: str, username: Optional[str]=None, is_warning: int = 0):
        await self.append_user(user_id=user_id, username=username)

        await self.db.execute(
            "INSERT INTO notes (user_id, content, timestamp, is_warning, staff_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, reason, datetime.datetime.now(), is_warning, staff_id)
        )
        await self.db.commit()

    
    async def record_ban(self, staff_id: int, user_id: Optional[int],  reason: str, unban_date: datetime.datetime, username: Optional[str] = None):
            await self.append_user(user_id=user_id, username=username)

            await self.db.execute(
                "INSERT INTO bans (user_id, content, ban_date, unban_date, staff_id) VALUES (?, ?, ?, ?, ?)",
                (user_id, reason, datetime.datetime.now(), unban_date, staff_id)
            )
            await self.db.commit()


    
    async def get_notes(self, user, isWarning: int = 0) -> UserNotes:
        user_id = await self.validate_inputs(user)
        cursor = await self.db.execute("""
    SELECT users.username, notes.staff_id, notes.content
    FROM notes
    INNER JOIN users ON notes.user_id = users.user_id
    WHERE notes.user_id = ? AND notes.is_warning = ?
""", (user_id,isWarning))
        rows = list(await cursor.fetchall())

        if not rows:
            return UserNotes(username="null", notes=[])

        username = str(user_id)
        if rows:
            username = rows[0][0]

        total_notes = []
        for note in rows:
            total_notes.append(Note(staff_id=note[1], content=note[2]))
        return UserNotes(username=username, notes=total_notes)


    async def get_warnings(self, user_id: Optional[int]):
        return await self.get_notes(user_id,isWarning = 1)
    

    
    async def get_ban_reason(self, user_id: Optional[int]):
        if self.db is None:
            raise RuntimeError("Database not connected!")

        cursor = await self.db.execute("SELECT content FROM bans WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None


    
    async def revoke_ban(self, user_id: Optional[int], silent: bool = False):
        if self.db is None:
            raise RuntimeError("Database not connected!")

        cursor = await self.db.execute("SELECT content FROM bans WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        ban_reason = row[0] if row else None

        await self.db.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))

        await self.db.commit()

        if silent == False:
             await self.record_note(user_id=user_id,reason=f"User was previously banned with the reason: {ban_reason}", staff_id=0) #NOTE STAFF ID SET TO 0. THIS SHOULD PROBABLY CHANGE IN THE FUTURE


    async def revoke_warning(self, user_id: Optional[int], warning_id: int):
        await self.revoke_note(user_id, warning_id)


    
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
    
db = ModDB(db_path=DB_PATH)