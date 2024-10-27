from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Model
from models.base import Base


class Author(Base, Model):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(512))
    phone: Mapped[str] = mapped_column(String(512))

    institution: Mapped[str] = mapped_column(String(1024))
