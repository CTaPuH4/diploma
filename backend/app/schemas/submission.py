from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.models.submission import SubmissionStatus, SubmissionLanguage


class SubmissionBase(BaseModel):
    code: str
    language: SubmissionLanguage = SubmissionLanguage.python


class InlineComment(BaseModel):
    line_start: int
    line_end: int
    text: str

    class Config:
        from_attributes = True


class TeacherSubmissionRead(SubmissionBase):
    user_id: int
    status: SubmissionStatus
    test_result: Optional[str] = None
    llm_comment: Optional[str] = None
    created_at: datetime
    inline_comments: List[InlineComment] = []

    class Config:
        from_attributes = True


class TeacherSubmissionUpdate(BaseModel):
    final_comment: Optional[str] = None
    grade: Optional[int] = None


class StudentSubmissionRead(SubmissionBase):
    id: int
    task_id: int
    status: SubmissionStatus
    final_comment: Optional[str] = None
    grade: Optional[int] = None
    created_at: datetime
    inline_comments: List[InlineComment] = []

    class Config:
        from_attributes = True
