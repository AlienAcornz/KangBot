from pydantic import BaseModel
from typing import Optional, List, Tuple

class Note(BaseModel):
    staff_id: int
    content: str

class UserNotes(BaseModel):
    username: str
    notes: List[Note]
    isWarning: bool = False