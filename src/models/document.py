from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Model
from models.base import Base


class Document(Base, Model):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(1024))

    document_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("document_types.id")
    )

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))

    authors: Mapped[list["DocumentAuthor"]] = relationship("DocumentAuthor")
    topics: Mapped[list["DocumentTopic"]] = relationship("DocumentTopic")
    document_type: Mapped["DocumentType"] = relationship("DocumentType")


class DocumentAuthor(Base, Model):
    __tablename__ = "document_authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"))
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("authors.id"))


class DocumentTopic(Base, Model):
    __tablename__ = "document_topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"))
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey("topics.id"))


class DocumentType(Base, Model):
    __tablename__ = "document_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))


class DocumentFile(Base, Model):
    __tablename__ = "document_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"))
    file_name: Mapped[str] = mapped_column(String(255))