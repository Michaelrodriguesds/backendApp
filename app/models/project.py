from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ProjectBase(BaseModel):
    title: str
    description: str
    category: str
    required_value: float
    applied_value: float = 0.0
    start_date: datetime

class ProjectCreate(ProjectBase):
    pass

class ProjectDB(ProjectBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    progress: float = 0.0

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    required_value: Optional[float] = None
    applied_value: Optional[float] = None
    start_date: Optional[datetime] = None
