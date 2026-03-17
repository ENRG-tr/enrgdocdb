from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String, Text

from ..database import Model
from .base import Base
from .user import Organization, User

WIKI_CONTENT_SIZE = 1024 * 32


class WikiPage(Model):
    __tablename__ = "wiki_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(512), nullable=False, unique=True, index=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("wiki_pages.id"), index=True
    )
    content: Mapped[str] = mapped_column(
        Text(WIKI_CONTENT_SIZE), nullable=False, default=""
    )
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))

    parent_page: Mapped["WikiPage | None"] = relationship(
        "WikiPage",
        foreign_keys=[parent_id],
        back_populates="child_pages",
        remote_side=[id],
    )
    child_pages: Mapped[list["WikiPage"]] = relationship(
        "WikiPage",
        back_populates="parent_page",
        cascade="all, delete-orphan",
    )
    revisions: Mapped[list["WikiRevision"]] = relationship(
        "WikiRevision",
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="WikiRevision.created_at.desc()",
    )
    organization: Mapped["Organization | None"] = relationship("Organization")

    def __repr__(self) -> str:
        return self.title


class WikiRevision(Base, Model):
    __tablename__ = "wiki_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("wiki_pages.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text(WIKI_CONTENT_SIZE), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1024))

    page: Mapped["WikiPage"] = relationship("WikiPage")
    author: Mapped["User"] = relationship("User")  # type: ignore
