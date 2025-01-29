from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Model
from models.author import Author
from models.base import Base
from models.topic import Topic
from models.user import Organization, User


class Document(Base, Model):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(1024))
    abstract: Mapped[str | None] = mapped_column(String(8192))

    document_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("document_types.id")
    )

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id")
    )

    user: Mapped[User] = relationship("User")
    document_authors: Mapped[list["DocumentAuthor"]] = relationship(
        "DocumentAuthor", back_populates="document", cascade="all, delete-orphan"
    )
    document_topics: Mapped[list["DocumentTopic"]] = relationship(
        "DocumentTopic", back_populates="document", cascade="all, delete-orphan"
    )
    files: Mapped[list["DocumentFile"]] = relationship(
        "DocumentFile", back_populates="document", cascade="all, delete-orphan"
    )
    document_type: Mapped["DocumentType"] = relationship("DocumentType")

    topics: Mapped[list["Topic"]] = association_proxy(
        "document_topics", "topic", creator=lambda topic: DocumentTopic(topic=topic)
    )  #  type: ignore
    authors: Mapped[list["Author"]] = association_proxy(
        "document_authors",
        "author",
        creator=lambda author: DocumentAuthor(author=author),
    )  #  type: ignore
    organization: Mapped[Organization] = relationship("Organization")

    def __repr__(self) -> str:
        return self.title


class DocumentAuthor(Base, Model):
    __tablename__ = "document_authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"))
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("authors.id"))

    author: Mapped[Author] = relationship("Author")
    document: Mapped[Document] = relationship(back_populates="document_authors")


class DocumentTopic(Base, Model):
    __tablename__ = "document_topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"))
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey("topics.id"))

    topic: Mapped[Topic] = relationship("Topic")
    document: Mapped[Document] = relationship()


class DocumentType(Base, Model):
    __tablename__ = "document_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

    def __repr__(self) -> str:
        return self.name


class DocumentFile(Base, Model):
    __tablename__ = "document_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    real_file_name: Mapped[str] = mapped_column(String(512))

    document: Mapped["Document"] = relationship()

    def __repr__(self) -> str:
        return self.file_name
