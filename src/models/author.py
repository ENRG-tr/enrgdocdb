from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Model
from models.base import Base


class Author(Base, Model):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(512), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(512), nullable=True)

    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey("institutions.id"))
    institution: Mapped["Institution"] = relationship("Institution")

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return self.name


class Institution(Base, Model):
    __tablename__ = "institutions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

    def __repr__(self) -> str:
        return self.name
