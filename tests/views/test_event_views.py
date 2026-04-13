"""
View tests for Event operations.

Tests event viewing, calendar export, and permission enforcement.
"""
from datetime import datetime, timedelta
from unittest.mock import patch
import jwt

from src.enrgdocdb.models.event import Event


class TestEventView:
    """Tests for individual event view."""

    def test_view_event_requires_authentication(self, client):
        """Test that viewing an event requires authentication."""
        response = client.get("/events/view/1")
        assert response.status_code in [302, 403, 404]

    def test_view_event_404_for_nonexistent(self, authenticated_client):
        """Test that viewing nonexistent event returns 404."""
        response = authenticated_client.get("/events/view/99999")
        assert response.status_code == 404

    def test_view_event_requires_permission(self, authenticated_client, db_session, user, organization):
        """Test that viewing an event requires VIEW permission."""
        event = Event(
            title="Test Event",
            date=datetime.now() + timedelta(days=30),
            location="Test Location",
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/events/view/{event.id}")
            assert response.status_code == 403

    def test_view_event_shows_content(self, authenticated_client, db_session, user, organization):
        """Test that event view shows event content."""
        event = Event(
            title="Test Event for Viewing",
            date=datetime.now() + timedelta(days=30),
            location="Test Location",
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()

        response = authenticated_client.get(f"/events/view/{event.id}")
        assert response.status_code == 200
        assert b"Test Event for Viewing" in response.data


class TestEventCalendar:
    """Tests for event calendar view."""

    def test_calendar_requires_authentication(self, client):
        """Test that calendar view requires authentication."""
        response = client.get("/events/calendar")
        assert response.status_code in [302, 403, 404]

    def test_calendar_shows_events(self, authenticated_client, db_session, user, organization):
        """Test that calendar view shows user's events."""
        event1 = Event(
            title="Event 1",
            date=datetime.now() + timedelta(days=30),
            location="Location 1",
            organization_id=organization.id,
        )
        event2 = Event(
            title="Event 2",
            date=datetime.now() + timedelta(days=60),
            location="Location 2",
            organization_id=organization.id,
        )
        db_session.add(event1)
        db_session.add(event2)
        db_session.commit()

        response = authenticated_client.get("/events/calendar")
        assert response.status_code == 200
        assert b"Event 1" in response.data
        assert b"Event 2" in response.data

    def test_calendar_shows_icalendar_url(self, authenticated_client, db_session, user, organization):
        """Test that calendar view includes iCalendar URL."""
        event = Event(
            title="Test Event",
            date=datetime.now() + timedelta(days=30),
            location="Test Location",
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()

        response = authenticated_client.get("/events/calendar")
        assert response.status_code == 200
        assert b"/events/icalendar/all/" in response.data


class TestICalendarExport:
    """Tests for iCalendar export endpoint."""

    def test_icalendar_all_requires_valid_token(self, client):
        """Test that iCalendar export requires valid JWT token."""
        response = client.get("/events/icalendar/all/invalid_token")
        assert response.status_code == 403

    def test_icalendar_all_returns_calendar(self, client, db_session, user, organization):
        """Test that iCalendar export returns valid calendar."""
        event = Event(
            title="Test Event",
            date=datetime.now() + timedelta(days=30),
            location="Test Location",
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()

        token = jwt.encode({"user_id": user.id}, "test-secret-key-for-unit-tests-only")
        response = client.get(f"/events/icalendar/all/{token}")
        
        assert response.status_code == 200
        assert b"BEGIN:VCALENDAR" in response.data
        assert b"BEGIN:VEVENT" in response.data
        assert b"Test Event" in response.data

    def test_icalendar_all_includes_event_details(self, client, db_session, user, organization):
        """Test that iCalendar export includes event details."""
        event = Event(
            title="Detailed Event",
            date=datetime.now() + timedelta(days=30),
            location="Conference Center",
            event_url="https://example.com/event",
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()

        token = jwt.encode({"user_id": user.id}, "test-secret-key-for-unit-tests-only")
        response = client.get(f"/events/icalendar/all/{token}")
        
        assert response.status_code == 200
        assert b"Conference Center" in response.data
        assert b"SUMMARY:Detailed Event" in response.data


class TestEventPermission:
    """Tests for event permission enforcement."""

    def test_event_view_403_without_permission(self, authenticated_client, db_session, user, organization):
        """Test that event view returns 403 without permission."""
        event = Event(
            title="Protected Event",
            date=datetime.now() + timedelta(days=30),
            organization_id=organization.id,
        )
        db_session.add(event)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/events/view/{event.id}")
            assert response.status_code == 403
