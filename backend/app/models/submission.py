from __future__ import annotations

import enum
from datetime import datetime

from app.database import Base
from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class SubmissionStatus(str, enum.Enum):
    submitted = "submitted"
    analyzing = "analyzing"
    on_review = "on_review"
    passed = "passed"
    failed = "failed"


class SubmissionLanguage(str, enum.Enum):
    python = "python"
    cpp = "cpp"
    other = "other"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tasks.id"), nullable=False
    )

    code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[SubmissionLanguage] = mapped_column(
        SQLEnum(SubmissionLanguage),
        nullable=False,
    )

    status: Mapped[SubmissionStatus] = mapped_column(
        SQLEnum(SubmissionStatus),
        default=SubmissionStatus.submitted,
    )
    test_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    final_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="submissions")
    task: Mapped["Task"] = relationship("Task", back_populates="submissions")
    inline_comments: Mapped[list["InlineComment"]] = relationship(
        "InlineComment", back_populates="submission", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Submission {self.id} by user {self.user_id}>"
