from app.database import Base
from sqlalchemy import Column
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import relationship


class InlineComment(Base):
    __tablename__ = "inline_comments"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)

    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)

    submission = relationship("Submission", back_populates="inline_comments")

    def __repr__(self):
        return f"<InlineComment {self.id} ({self.line_start}-{self.line_end})>"
