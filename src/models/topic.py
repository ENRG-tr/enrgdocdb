from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Model
from models.base import Base


class Topic(Base, Model):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id"), nullable=True
    )
    parent_topic: Mapped["Topic"] = relationship("Topic", remote_side=[id])
    child_topics: Mapped[list["Topic"]] = relationship(
        "Topic", back_populates="parent_topic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        if self.parent_topic:
            return f"{self.parent_topic.name} : {self.name}"
        return self.name
