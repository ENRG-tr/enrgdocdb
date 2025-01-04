from datetime import datetime, time, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Model
from models.base import Base
from models.document import Document
from models.topic import Topic
from models.user import User


class Event(Base, Model):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(1024))
    date: Mapped[datetime] = mapped_column(DateTime)
    location: Mapped[str] = mapped_column(String(1024))
    event_url: Mapped[str] = mapped_column(String(2048))

    event_topics: Mapped[list["EventTopic"]] = relationship(
        "EventTopic", back_populates="event", cascade="all, delete-orphan"
    )
    event_moderators: Mapped[list["EventModerator"]] = relationship(
        "EventModerator", back_populates="event", cascade="all, delete-orphan"
    )
    event_sessions: Mapped[list["EventSession"]] = relationship(
        "EventSession", back_populates="event", cascade="all, delete-orphan"
    )

    topics: Mapped[list["Topic"]] = association_proxy(
        "event_topics", "topic", creator=lambda topic: EventTopic(topic=topic)
    )  # type: ignore
    moderators: Mapped[list["User"]] = association_proxy(
        "event_moderators",
        "moderator",
        creator=lambda moderator: EventModerator(moderator=moderator),
    )  # type: ignore


class EventTopic(Base, Model):
    __tablename__ = "event_topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"))
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey("topics.id"))

    topic: Mapped[Topic] = relationship("Topic")
    event: Mapped[Event] = relationship()


class EventModerator(Base, Model):
    __tablename__ = "event_moderators"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"))
    moderator_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))

    moderator: Mapped[User] = relationship("User")
    event: Mapped[Event] = relationship()


class EventSession(Base, Model):
    __tablename__ = "event_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"))
    external_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    session_name: Mapped[str] = mapped_column(String(1024))
    session_time: Mapped[datetime] = mapped_column(DateTime)

    session_topics: Mapped[list["SessionTopic"]] = relationship(
        "SessionTopic", back_populates="session", cascade="all, delete-orphan"
    )
    session_moderators: Mapped[list["SessionModerator"]] = relationship(
        "SessionModerator", back_populates="session", cascade="all, delete-orphan"
    )
    talk_notes: Mapped[list["TalkNote"]] = relationship(
        "TalkNote", back_populates="session", cascade="all, delete-orphan"
    )

    topics: Mapped[list["Topic"]] = association_proxy(
        "session_topics", "topic", creator=lambda topic: SessionTopic(topic=topic)
    )  # type: ignore
    moderators: Mapped[list["User"]] = association_proxy(
        "session_moderators",
        "moderator",
        creator=lambda moderator: SessionModerator(moderator=moderator),
    )  # type: ignore
    event: Mapped[Event] = relationship()


class SessionTopic(Base, Model):
    __tablename__ = "session_topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("event_sessions.id"))
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey("topics.id"))

    topic: Mapped[Topic] = relationship("Topic")
    session: Mapped[EventSession] = relationship()


class SessionModerator(Base, Model):
    __tablename__ = "session_moderators"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("event_sessions.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))

    moderator: Mapped[User] = relationship("User")
    session: Mapped[EventSession] = relationship()


class TalkNote(Base, Model):
    __tablename__ = "talk_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("event_sessions.id"))
    talk_title: Mapped[str] = mapped_column(Text)
    start_time: Mapped[time] = mapped_column(Time, nullable=True)

    session: Mapped[EventSession] = relationship()
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), nullable=True
    )
    document: Mapped[Document] = relationship()
