"""
Tests for Event model and related functionality.
"""
from datetime import datetime, time, timedelta

from src.enrgdocdb.models.event import (
    Event,
    EventSession,
    EventTopic,
    EventModerator,
    SessionTopic,
    SessionModerator,
    TalkNote,
)
from src.enrgdocdb.models.topic import Topic
from src.enrgdocdb.models.document import Document, DocumentType


class TestEvent:
    """Test Event model."""
    
    def test_event_creation(self, db_session, event, organization):
        """Test creating an event."""
        assert event.id is not None
        assert event.title == "Test Event"
        assert event.organization_id == organization.id
    
    def test_event_with_organization(self, db_session, event, organization):
        """Test event with organization."""
        assert event.organization.id == organization.id
        assert event.organization.name == "Test Organization"
    
    def test_event_with_location(self, db_session, organization):
        """Test event with location."""
        event = Event(
            title="Event With Location",
            date=datetime.now() + timedelta(days=30),
            location="Conference Hall A",
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()
        
        assert event.location == "Conference Hall A"
    
    def test_event_without_location(self, db_session, organization):
        """Test event without location."""
        event = Event(
            title="Event Without Location",
            date=datetime.now() + timedelta(days=30),
            location=None,
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()
        
        assert event.location is None
    
    def test_event_with_url(self, db_session, organization):
        """Test event with URL."""
        event = Event(
            title="Event With URL",
            date=datetime.now() + timedelta(days=30),
            location="Conference Hall",
            event_url="https://example.com/event",
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()
        
        assert event.event_url == "https://example.com/event"
    
    def test_event_without_url(self, db_session, organization):
        """Test event without URL."""
        event = Event(
            title="Event Without URL",
            date=datetime.now() + timedelta(days=30),
            location="Conference Hall",
            event_url=None,
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()
        
        assert event.event_url is None
    
    def test_event_topics_relationship(self, db_session, event, topic):
        """Test event topics relationship."""
        event_topic = EventTopic(
            event_id=event.id,
            topic_id=topic.id,
        )
        event.event_topics.append(event_topic)
        db_session.commit()
        
        assert len(event.event_topics) == 1
        assert topic in event.topics
    
    def test_event_moderators_relationship(self, db_session, event, user):
        """Test event moderators relationship."""
        event_moderator = EventModerator(
            event_id=event.id,
            moderator_id=user.id,
        )
        event.event_moderators.append(event_moderator)
        db_session.commit()
        
        assert len(event.event_moderators) == 1
        assert user in event.moderators
    
    def test_event_sessions_relationship(self, db_session, event, event_session):
        """Test event sessions relationship."""
        assert len(event.event_sessions) == 1
        assert event.event_sessions[0].id == event_session.id
    
    def test_event_multiple_topics(self, db_session, event, topic):
        """Test event with multiple topics."""
        topic2 = Topic(name="Topic 2")
        db_session.add(topic2)
        db_session.commit()
        
        event_topic1 = EventTopic(event_id=event.id, topic_id=topic.id)
        event_topic2 = EventTopic(event_id=event.id, topic_id=topic2.id)
        event.event_topics.extend([event_topic1, event_topic2])
        db_session.commit()
        
        assert len(event.topics) == 2
        assert topic in event.topics
        assert topic2 in event.topics
    
    def test_event_multiple_moderators(self, db_session, event, user):
        """Test event with multiple moderators."""
        user2 = user.__class__(
            email="moderator2@example.com",
            username="moderator2",
            first_name="Moderator",
            last_name="Two",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_mod2",
        )
        db_session.add(user2)
        db_session.commit()
        
        mod1 = EventModerator(event_id=event.id, moderator_id=user.id)
        mod2 = EventModerator(event_id=event.id, moderator_id=user2.id)
        event.event_moderators.extend([mod1, mod2])
        db_session.commit()
        
        assert len(event.moderators) == 2
        assert user in event.moderators
        assert user2 in event.moderators
    
    def test_event_add_topic_via_proxy(self, db_session, event, topic):
        """Test adding topic via association proxy."""
        event.topics.append(topic)
        db_session.commit()
        
        assert topic in event.topics
        assert len(event.event_topics) == 1
    
    def test_event_add_moderator_via_proxy(self, db_session, event, user):
        """Test adding moderator via association proxy."""
        event.moderators.append(user)
        db_session.commit()
        
        assert user in event.moderators
        assert len(event.event_moderators) == 1
    
    def test_event_cascade_delete_topics(self, db_session, event, topic):
        """Test that event topics are deleted when event is deleted."""
        event_topic = EventTopic(
            event_id=event.id,
            topic_id=topic.id,
        )
        event.event_topics.append(event_topic)
        db_session.commit()
        
        event_topic_id = event_topic.id
        event_id = event.id
        
        db_session.delete(event)
        db_session.commit()
        
        # EventTopic should be deleted due to cascade
        deleted_topic = db_session.query(EventTopic).get(event_topic_id)
        assert deleted_topic is None
    
    def test_event_cascade_delete_moderators(self, db_session, event, user):
        """Test that event moderators are deleted when event is deleted."""
        event_moderator = EventModerator(
            event_id=event.id,
            moderator_id=user.id,
        )
        event.event_moderators.append(event_moderator)
        db_session.commit()
        
        event_moderator_id = event_moderator.id
        
        db_session.delete(event)
        db_session.commit()
        
        # EventModerator should be deleted due to cascade
        deleted_moderator = db_session.query(EventModerator).get(event_moderator_id)
        assert deleted_moderator is None
    
    def test_event_cascade_delete_sessions(self, db_session, event, event_session):
        """Test that event sessions are deleted when event is deleted."""
        session_id = event_session.id
        
        db_session.delete(event)
        db_session.commit()
        
        # EventSession should be deleted due to cascade
        deleted_session = db_session.query(EventSession).get(session_id)
        assert deleted_session is None


class TestEventSession:
    """Test EventSession model."""
    
    def test_event_session_creation(self, db_session, event_session, event):
        """Test creating an event session."""
        assert event_session.id is not None
        assert event_session.event_id == event.id
        assert event_session.session_name == "Test Session"
    
    def test_event_session_with_event(self, db_session, event_session, event):
        """Test event session with event."""
        assert event_session.event.id == event.id
        assert event_session.event.title == "Test Event"
    
    def test_event_session_with_external_url(self, db_session, event):
        """Test event session with external URL."""
        session = EventSession(
            event_id=event.id,
            session_name="Session With URL",
            session_time=datetime.now() + timedelta(days=30, hours=2),
            external_url="https://example.com/session",
        )
        db_session.add(session)
        db_session.commit()
        
        assert session.external_url == "https://example.com/session"
    
    def test_event_session_without_external_url(self, db_session, event):
        """Test event session without external URL."""
        session = EventSession(
            event_id=event.id,
            session_name="Session Without URL",
            session_time=datetime.now() + timedelta(days=30, hours=2),
            external_url=None,
        )
        db_session.add(session)
        db_session.commit()
        
        assert session.external_url is None
    
    def test_event_session_topics_relationship(self, db_session, event_session, topic):
        """Test event session topics relationship."""
        session_topic = SessionTopic(
            session_id=event_session.id,
            topic_id=topic.id,
        )
        event_session.session_topics.append(session_topic)
        db_session.commit()
        
        assert len(event_session.session_topics) == 1
        assert topic in event_session.topics
    
    def test_event_session_moderators_relationship(self, db_session, event_session, user):
        """Test event session moderators relationship."""
        session_moderator = SessionModerator(
            session_id=event_session.id,
            user_id=user.id,
        )
        event_session.session_moderators.append(session_moderator)
        db_session.commit()
        
        assert len(event_session.session_moderators) == 1
        assert user in event_session.moderators
    
    def test_event_session_talk_notes_relationship(self, db_session, event_session):
        """Test event session talk notes relationship."""
        note = TalkNote(
            session_id=event_session.id,
            talk_title="Talk Title",
            start_time=time(10, 0),
        )
        event_session.talk_notes.append(note)
        db_session.commit()
        
        assert len(event_session.talk_notes) == 1
    
    def test_event_session_multiple_topics(self, db_session, event_session, topic):
        """Test event session with multiple topics."""
        topic2 = Topic(name="Topic 2")
        db_session.add(topic2)
        db_session.commit()
        
        st1 = SessionTopic(session_id=event_session.id, topic_id=topic.id)
        st2 = SessionTopic(session_id=event_session.id, topic_id=topic2.id)
        event_session.session_topics.extend([st1, st2])
        db_session.commit()
        
        assert len(event_session.topics) == 2
        assert topic in event_session.topics
        assert topic2 in event_session.topics
    
    def test_event_session_multiple_moderators(self, db_session, event_session, user):
        """Test event session with multiple moderators."""
        user2 = user.__class__(
            email="mod2@example.com",
            username="mod2",
            first_name="Moderator",
            last_name="Two",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_mod2",
        )
        db_session.add(user2)
        db_session.commit()
        
        sm1 = SessionModerator(session_id=event_session.id, user_id=user.id)
        sm2 = SessionModerator(session_id=event_session.id, user_id=user2.id)
        event_session.session_moderators.extend([sm1, sm2])
        db_session.commit()
        
        assert len(event_session.moderators) == 2
        assert user in event_session.moderators
        assert user2 in event_session.moderators
    
    def test_event_session_add_topic_via_proxy(self, db_session, event_session, topic):
        """Test adding topic via association proxy."""
        event_session.topics.append(topic)
        db_session.commit()
        
        assert topic in event_session.topics
        assert len(event_session.session_topics) == 1
    
    def test_event_session_add_moderator_via_proxy(self, db_session, event_session, user):
        """Test adding moderator via association proxy."""
        event_session.moderators.append(user)
        db_session.commit()
        
        assert user in event_session.moderators
        assert len(event_session.session_moderators) == 1
    
    def test_event_session_cascade_delete_topics(self, db_session, event_session, topic):
        """Test that session topics are deleted when session is deleted."""
        session_topic = SessionTopic(
            session_id=event_session.id,
            topic_id=topic.id,
        )
        event_session.session_topics.append(session_topic)
        db_session.commit()
        
        session_topic_id = session_topic.id
        
        db_session.delete(event_session)
        db_session.commit()
        
        # SessionTopic should be deleted due to cascade
        deleted_topic = db_session.query(SessionTopic).get(session_topic_id)
        assert deleted_topic is None
    
    def test_event_session_cascade_delete_moderators(self, db_session, event_session, user):
        """Test that session moderators are deleted when session is deleted."""
        session_moderator = SessionModerator(
            session_id=event_session.id,
            user_id=user.id,
        )
        event_session.session_moderators.append(session_moderator)
        db_session.commit()
        
        session_moderator_id = session_moderator.id
        
        db_session.delete(event_session)
        db_session.commit()
        
        # SessionModerator should be deleted due to cascade
        deleted_moderator = db_session.query(SessionModerator).get(session_moderator_id)
        assert deleted_moderator is None
    
    def test_event_session_cascade_delete_talk_notes(self, db_session, event_session):
        """Test that talk notes are deleted when session is deleted."""
        note = TalkNote(
            session_id=event_session.id,
            talk_title="Talk Title",
            start_time=time(10, 0),
        )
        event_session.talk_notes.append(note)
        db_session.commit()
        
        note_id = note.id
        
        db_session.delete(event_session)
        db_session.commit()
        
        # TalkNote should be deleted due to cascade
        deleted_note = db_session.query(TalkNote).get(note_id)
        assert deleted_note is None


class TestEventTopic:
    """Test EventTopic model."""
    
    def test_event_topic_creation(self, db_session, event, topic):
        """Test creating an event topic."""
        event_topic = EventTopic(
            event_id=event.id,
            topic_id=topic.id,
        )
        db_session.add(event_topic)
        db_session.commit()
        
        assert event_topic.id is not None
        assert event_topic.event_id == event.id
        assert event_topic.topic_id == topic.id
    
    def test_event_topic_event_relationship(self, db_session, event, topic):
        """Test event topic event relationship."""
        event_topic = EventTopic(
            event_id=event.id,
            topic_id=topic.id,
        )
        db_session.add(event_topic)
        db_session.commit()
        
        assert event_topic.event.id == event.id
        assert event_topic.event.title == "Test Event"
    
    def test_event_topic_topic_relationship(self, db_session, event, topic):
        """Test event topic topic relationship."""
        event_topic = EventTopic(
            event_id=event.id,
            topic_id=topic.id,
        )
        db_session.add(event_topic)
        db_session.commit()
        
        assert event_topic.topic.id == topic.id
        assert event_topic.topic.name == "Test Topic"


class TestEventModerator:
    """Test EventModerator model."""
    
    def test_event_moderator_creation(self, db_session, event, user):
        """Test creating an event moderator."""
        event_moderator = EventModerator(
            event_id=event.id,
            moderator_id=user.id,
        )
        db_session.add(event_moderator)
        db_session.commit()
        
        assert event_moderator.id is not None
        assert event_moderator.event_id == event.id
        assert event_moderator.moderator_id == user.id
    
    def test_event_moderator_event_relationship(self, db_session, event, user):
        """Test event moderator event relationship."""
        event_moderator = EventModerator(
            event_id=event.id,
            moderator_id=user.id,
        )
        db_session.add(event_moderator)
        db_session.commit()
        
        assert event_moderator.event.id == event.id
        assert event_moderator.event.title == "Test Event"
    
    def test_event_moderator_moderator_relationship(self, db_session, event, user):
        """Test event moderator moderator relationship."""
        event_moderator = EventModerator(
            event_id=event.id,
            moderator_id=user.id,
        )
        db_session.add(event_moderator)
        db_session.commit()
        
        assert event_moderator.moderator.id == user.id
        assert event_moderator.moderator.email == user.email


class TestSessionTopic:
    """Test SessionTopic model."""
    
    def test_session_topic_creation(self, db_session, event_session, topic):
        """Test creating a session topic."""
        session_topic = SessionTopic(
            session_id=event_session.id,
            topic_id=topic.id,
        )
        db_session.add(session_topic)
        db_session.commit()
        
        assert session_topic.id is not None
        assert session_topic.session_id == event_session.id
        assert session_topic.topic_id == topic.id
    
    def test_session_topic_session_relationship(self, db_session, event_session, topic):
        """Test session topic session relationship."""
        session_topic = SessionTopic(
            session_id=event_session.id,
            topic_id=topic.id,
        )
        db_session.add(session_topic)
        db_session.commit()
        
        assert session_topic.session.id == event_session.id
        assert session_topic.session.session_name == "Test Session"
    
    def test_session_topic_topic_relationship(self, db_session, event_session, topic):
        """Test session topic topic relationship."""
        session_topic = SessionTopic(
            session_id=event_session.id,
            topic_id=topic.id,
        )
        db_session.add(session_topic)
        db_session.commit()
        
        assert session_topic.topic.id == topic.id
        assert session_topic.topic.name == "Test Topic"


class TestSessionModerator:
    """Test SessionModerator model."""
    
    def test_session_moderator_creation(self, db_session, event_session, user):
        """Test creating a session moderator."""
        session_moderator = SessionModerator(
            session_id=event_session.id,
            user_id=user.id,
        )
        db_session.add(session_moderator)
        db_session.commit()
        
        assert session_moderator.id is not None
        assert session_moderator.session_id == event_session.id
        assert session_moderator.user_id == user.id
    
    def test_session_moderator_session_relationship(self, db_session, event_session, user):
        """Test session moderator session relationship."""
        session_moderator = SessionModerator(
            session_id=event_session.id,
            user_id=user.id,
        )
        db_session.add(session_moderator)
        db_session.commit()
        
        assert session_moderator.session.id == event_session.id
        assert session_moderator.session.session_name == "Test Session"
    
    def test_session_moderator_moderator_relationship(self, db_session, event_session, user):
        """Test session moderator moderator relationship."""
        session_moderator = SessionModerator(
            session_id=event_session.id,
            user_id=user.id,
        )
        db_session.add(session_moderator)
        db_session.commit()
        
        assert session_moderator.moderator.id == user.id
        assert session_moderator.moderator.email == user.email


class TestTalkNote:
    """Test TalkNote model."""
    
    def test_talk_note_creation(self, db_session, event_session):
        """Test creating a talk note."""
        note = TalkNote(
            session_id=event_session.id,
            talk_title="Talk Title",
            start_time=time(10, 0),
        )
        db_session.add(note)
        db_session.commit()
        
        assert note.id is not None
        assert note.session_id == event_session.id
        assert note.talk_title == "Talk Title"
    
    def test_talk_note_with_session(self, db_session, event_session):
        """Test talk note with session."""
        note = TalkNote(
            session_id=event_session.id,
            talk_title="Talk Title",
            start_time=time(10, 0),
        )
        db_session.add(note)
        db_session.commit()
        
        assert note.session.id == event_session.id
        assert note.session.session_name == "Test Session"
    
    def test_talk_note_without_start_time(self, db_session, event_session):
        """Test talk note without start time."""
        note = TalkNote(
            session_id=event_session.id,
            talk_title="Talk Without Time",
            start_time=None,
        )
        db_session.add(note)
        db_session.commit()
        
        assert note.start_time is None
    
    def test_talk_note_with_document(self, db_session, event_session):
        """Test talk note with document."""
        doc_type = DocumentType(name="Conference Paper")
        document = Document(
            title="Test Document",
            document_type=doc_type,
            user_id=1,
            organization_id=1,
        )
        db_session.add_all([doc_type, document])
        db_session.commit()
        
        note = TalkNote(
            session_id=event_session.id,
            talk_title="Talk With Document",
            start_time=time(10, 0),
            document_id=document.id,
        )
        db_session.add(note)
        db_session.commit()
        
        assert note.document_id == document.id
        assert note.document.id == document.id
    
    def test_talk_note_without_document(self, db_session, event_session):
        """Test talk note without document."""
        note = TalkNote(
            session_id=event_session.id,
            talk_title="Talk Without Document",
            start_time=time(10, 0),
            document_id=None,
        )
        db_session.add(note)
        db_session.commit()
        
        assert note.document_id is None
        assert note.document is None
    
    def test_talk_note_cascade_delete_on_session_delete(self, db_session, event_session):
        """Test that talk notes are deleted when session is deleted."""
        note = TalkNote(
            session_id=event_session.id,
            talk_title="Talk Title",
            start_time=time(10, 0),
        )
        db_session.add(note)
        db_session.commit()
        
        note_id = note.id
        
        db_session.delete(event_session)
        db_session.commit()
        
        # TalkNote should be deleted due to cascade
        deleted_note = db_session.query(TalkNote).get(note_id)
        assert deleted_note is None
