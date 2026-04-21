from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    text: str
    deadline: Optional[datetime] = None
    group_id: int


class TaskRead(BaseModel):
    id: int
    title: str
    text: str
    deadline: Optional[datetime] = None
    group_id: int
    created_by_id: int

    class Config:
        from_attributes = True
