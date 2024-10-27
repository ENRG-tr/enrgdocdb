from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Model
from models.base import Base


class Topic(Base, Model):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
