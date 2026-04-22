from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from app.models.submission import SubmissionStatus, SubmissionLanguage


class SubmissionBase(BaseModel):
    task_id: int
    code: str
    language: SubmissionLanguage = SubmissionLanguage.python


class SubmissionResponse(SubmissionBase):
    id: int
    user_id: int
    status: SubmissionStatus
    created_at: datetime

    class Config:
        from_attributes = True


class InlineComment(BaseModel):
    line_start: int
    line_end: int
    text: str

    class Config:
        from_attributes = True


class TeacherSubmissionRead(SubmissionBase):
    id: int
    user_id: int
    status: SubmissionStatus
    test_result: Optional[str] = None
    llm_comment: Optional[str] = None
    created_at: datetime
    inline_comments: List[InlineComment] = []

    class Config:
        from_attributes = True


class TeacherSubmissionUpdate(BaseModel):
    final_comment: str
    grade: int = Field(ge=1, le=54)


class StudentSubmissionRead(SubmissionBase):
    id: int
    status: SubmissionStatus
    final_comment: Optional[str] = None
    grade: Optional[int] = None
    created_at: datetime
    inline_comments: List[InlineComment] = []

    class Config:
        from_attributes = True
