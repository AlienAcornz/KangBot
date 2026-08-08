from pydantic import BaseModel
from typing import Optional, List, Tuple
import datetime

class Note(BaseModel):
    staff_id: int
    content: str
    note_id: int
    timestamp: datetime.datetime

class UserNotes(BaseModel):
    username: str
    notes: List[Note]
    isWarning: bool = False


class Ban(BaseModel):
    reason: str
    ban_date: datetime.datetime | None
    unban_date: datetime.datetime | None
    staff_id: int
    username: str