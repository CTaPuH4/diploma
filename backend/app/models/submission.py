import enum
from datetime import datetime

from app.database import Base
from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    testing = "testing"
    llm_analyzing = "llm_analyzing"
    completed = "completed"
    error = "error"


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    code = Column(Text, nullable=False)
    language = Column(String, nullable=False)           # "python", "cpp" и т.д.

    status = Column(SQLEnum(SubmissionStatus), default=SubmissionStatus.pending)
    test_result = Column(Text, nullable=True)           # JSON с результатами тестов
    llm_comment = Column(Text, nullable=True)           # комментарий от LLM
    final_comment = Column(Text, nullable=True)         # финальный комментарий
    grade = Column(Integer, nullable=True)              # оценка

    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    user = relationship("User", back_populates="submissions")
    task = relationship("Task", back_populates="submissions")
    inline_comments = relationship(
        "InlineComment", back_populates="submission", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Submission {self.id} by user {self.user_id}>"
