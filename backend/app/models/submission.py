import enum
from sqlalchemy.sql import func

from app.database import Base
from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import relationship


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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    code = Column(Text, nullable=False)
    language = Column(SQLEnum(SubmissionLanguage), nullable=False)

    status = Column(SQLEnum(SubmissionStatus), default=SubmissionStatus.submitted)
    test_result = Column(Text, nullable=True)          # JSON с результатами тестов
    llm_comment = Column(Text, nullable=True)           # комментарий от LLM
    final_comment = Column(Text, nullable=True)         # финальный комментарий
    grade = Column(Integer, nullable=True)              # оценка

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    user = relationship("User", back_populates="submissions")
    task = relationship("Task", back_populates="submissions")
    inline_comments = relationship(
        "InlineComment", back_populates="submission", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Submission {self.id} by user {self.user_id}>"
