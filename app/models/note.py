from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class NoteBase(BaseModel):
    title: str
    content: str
    date: Optional[datetime] = None

class NoteCreate(NoteBase):
    pass

class NoteDB(NoteBase):
    id: str
    user_id: str
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[datetime] = None
