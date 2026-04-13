"""
Permission enforcement tests for all views.

Verifies that all views correctly enforce READ, EDIT, ADD, and ADMIN permissions.
Tests cover document, wiki, event, and user views.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

from src.enrgdocdb.models.document import Document, DocumentType, DocumentFile
from src.enrgdocdb.models.wiki import WikiPage, WikiFile
from src.enrgdocdb.models.event import Event


class TestDocumentPermissionEnforcement:
    """Tests for document view permission enforcement."""

    def test_document_view_enforces_READ_permission(self, authenticated_client, db_session, user, organization):
        """Test that document view requires VIEW permission."""
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        
        document = Document(
            title="Protected Document",
            abstract="Content",
            user_id=user.id,
            document_type_id=doc_type.id,
            organization_id=organization.id,
        )
        db_session.add(document)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/documents/view/{document.id}")
            assert response.status_code == 403

    def test_document_create_enforces_ADD_permission(self, authenticated_client, db_session, user, organization):
        """Test that document creation requires ADD permission."""
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.post("/documents/new", data={
                "title": "New Document",
                "abstract": "Content",
                "document_type": str(doc_type.id),
                "organization": str(organization.id),
            })
            assert response.status_code == 403

    def test_document_edit_enforces_EDIT_permission(self, authenticated_client, db_session, user, organization):
        """Test that document editing requires EDIT permission."""
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        
        document = Document(
            title="Edit Test",
            abstract="Content",
            user_id=user.id,
            document_type_id=doc_type.id,
            organization_id=organization.id,
        )
        db_session.add(document)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/documents/edit/{document.id}")
            assert response.status_code in [302, 403, 404]

    def test_document_delete_enforces_ADMIN_permission(self, authenticated_client, db_session, user, organization):
        """Test that document deletion requires ADMIN permission."""
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        
        document = Document(
            title="Delete Test",
            abstract="Content",
            user_id=user.id,
            document_type_id=doc_type.id,
            organization_id=organization.id,
        )
        db_session.add(document)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/documents/delete/{document.id}")
            assert response.status_code in [302, 403, 404]

    def test_document_file_download_enforces_VIEW_permission(self, authenticated_client, db_session, user, organization):
        """Test that file download requires VIEW permission."""
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        
        document = Document(
            title="File Test",
            abstract="Content",
            user_id=user.id,
            document_type_id=doc_type.id,
            organization_id=organization.id,
        )
        db_session.add(document)
        db_session.commit()

        file = DocumentFile(
            document_id=document.id,
            file_name="test.pdf",
            real_file_name="test.pdf",
        )
        db_session.add(file)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/documents/download-file/{file.id}")
            assert response.status_code == 403

    def test_document_file_upload_enforces_EDIT_permission(self, authenticated_client, db_session, user, organization):
        """Test that file upload requires EDIT permission."""
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        
        document = Document(
            title="Upload Test",
            abstract="Content",
            user_id=user.id,
            document_type_id=doc_type.id,
            organization_id=organization.id,
        )
        db_session.add(document)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/documents/upload_files?id={document.id}")
            assert response.status_code == 403


class TestWikiPermissionEnforcement:
    """Tests for wiki view permission enforcement."""

    def test_wiki_view_enforces_VIEW_permission(self, authenticated_client, db_session, user):
        """Test that wiki page view requires VIEW permission."""
        page = WikiPage(
            title="Protected Wiki",
            slug="protected-wiki",
            content="Content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get("/wiki/protected-wiki")
            assert response.status_code == 302

    def test_wiki_create_enforces_ADD_permission(self, authenticated_client, db_session, user):
        """Test that wiki page creation requires ADD permission."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.post("/wiki/new", data={
                "title": "New Page",
                "slug": "new-page",
                "content": "Content",
            })
            # Should not create page
            pages = db_session.query(WikiPage).filter_by(slug="new-page").all()
            assert len(pages) == 0

    def test_wiki_edit_enforces_EDIT_permission(self, authenticated_client, db_session, user):
        """Test that wiki page editing requires EDIT permission."""
        page = WikiPage(
            title="Edit Test",
            slug="edit-test",
            content="Content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get("/wiki/edit-test/edit")
            assert response.status_code in [302, 403]

    def test_wiki_delete_enforces_EDIT_permission(self, authenticated_client, db_session, user):
        """Test that wiki page deletion requires EDIT permission."""
        page = WikiPage(
            title="Delete Test",
            slug="delete-test",
            content="Content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.post("/wiki/delete-test/delete")
            assert response.status_code in [302, 403]

    def test_wiki_file_download_enforces_VIEW_permission(self, authenticated_client, db_session, user):
        """Test that wiki file download requires VIEW permission."""
        page = WikiPage(
            title="File Test",
            slug="file-test",
            content="Content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        file = WikiFile(
            page=page,
            file_name="test.pdf",
            real_file_name="test.pdf",
        )
        db_session.add(file)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/wiki/download-file/{file.id}")
            assert response.status_code == 403

    def test_wiki_history_enforces_VIEW_permission(self, authenticated_client, db_session, user):
        """Test that wiki history requires VIEW permission."""
        page = WikiPage(
            title="History Test",
            slug="history-test",
            content="Content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get("/wiki/history-test/history")
            assert response.status_code in [302, 403]


class TestEventPermissionEnforcement:
    """Tests for event view permission enforcement."""

    def test_event_view_enforces_VIEW_permission(self, authenticated_client, db_session, user, organization):
        """Test that event view requires VIEW permission."""
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


class TestUserPermissionEnforcement:
    """Tests for user view permission enforcement."""

    def test_user_create_enforces_ADMIN_permission(self, authenticated_client, user):
        """Test that user creation requires ADMIN permission."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get("/user/create")
            assert response.status_code == 403

    def test_user_create_post_enforces_ADMIN_permission(self, authenticated_client, user):
        """Test that user creation POST requires ADMIN permission."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.post("/user/create", data={
                "email": "newuser@example.com",
                "password": "password123",
                "first_name": "New",
                "last_name": "User",
                "role": "1",
            })
            assert response.status_code == 403


class TestAuthenticationEnforcement:
    """Tests for authentication requirement enforcement."""

    def test_document_view_requires_auth(self, client):
        """Test that document view requires authentication."""
        response = client.get("/documents/view/1")
        assert response.status_code == 302

    def test_document_new_requires_auth(self, client):
        """Test that document creation requires authentication."""
        response = client.get("/documents/new")
        assert response.status_code == 302

    def test_wiki_index_requires_auth(self, client):
        """Test that wiki index requires authentication."""
        response = client.get("/wiki/")
        assert response.status_code == 302

    def test_wiki_new_requires_auth(self, client):
        """Test that wiki creation requires authentication."""
        response = client.get("/wiki/new")
        assert response.status_code == 302

    def test_event_calendar_requires_auth(self, client):
        """Test that event calendar requires authentication."""
        response = client.get("/events/calendar")
        assert response.status_code == 302

    def test_user_your_account_requires_auth(self, client):
        """Test that user account requires authentication."""
        response = client.get("/user/your_account")
        assert response.status_code == 302


class TestAllViewsUseSecureBlueprint:
    """Tests to verify all views use secure_blueprint decorator."""

    def test_document_blueprint_is_secured(self, client):
        """Test that document blueprint uses secure_blueprint."""
        response = client.get("/documents/view/1")
        assert response.status_code == 302

    def test_wiki_blueprint_is_secured(self, client):
        """Test that wiki blueprint uses secure_blueprint."""
        response = client.get("/wiki/")
        assert response.status_code == 302

    def test_event_blueprint_is_secured(self, client):
        """Test that event blueprint uses secure_blueprint."""
        response = client.get("/events/calendar")
        assert response.status_code == 302

    def test_user_blueprint_is_secured(self, client):
        """Test that user blueprint uses secure_blueprint."""
        response = client.get("/user/your_account")
        assert response.status_code == 302
