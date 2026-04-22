from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TestCaseCreate(BaseModel):
    input: str
    output: str
    is_hidden: bool = False


class TaskCreate(BaseModel):
    title: str
    text: str
    deadline: Optional[datetime] = None
    group_id: int
    test_cases: List[TestCaseCreate] = []


class TaskRead(BaseModel):
    id: int
    title: str
    text: str
    deadline: Optional[datetime] = None
    group_id: int
    created_by_id: int

    class Config:
        from_attributes = True


class TestCaseRead(BaseModel):
    id: int
    input: str
    output: str
    is_hidden: bool = False

    class Config:
        from_attributes = True


class TaskDetailRead(BaseModel):
    id: int
    title: str
    text: str
    deadline: Optional[datetime] = None
    group_id: int
    created_by_id: int

    test_cases: List[TestCaseRead] = []

    class Config:
        from_attributes = True
