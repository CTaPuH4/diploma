from __future__ import annotations

from app.database import Base
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class InlineComment(Base):
    __tablename__ = "inline_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("submissions.id"), nullable=False
    )

    line_start: Mapped[int] = mapped_column(Integer, nullable=False)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    submission: Mapped["Submission"] = relationship(
        "Submission",
        back_populates="inline_comments",
    )

    def __repr__(self):
        return f"<InlineComment {self.id} ({self.line_start}-{self.line_end})>"
