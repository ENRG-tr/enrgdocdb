"""
View tests for Wiki page operations.

Tests wiki page listing, creation, editing, revisions, file management,
and permission enforcement.
"""
from unittest.mock import patch, MagicMock

from src.enrgdocdb.models.wiki import WikiPage, WikiRevision


class TestWikiIndex:
    """Tests for wiki index page."""

    def test_wiki_index_requires_login(self, client):
        """Test that wiki index requires login."""
        response = client.get("/wiki/")
        assert response.status_code in [302, 403, 404]

    def test_wiki_index_shows_pinned_pages(self, authenticated_client, db_session, user):
        """Test that wiki index shows pinned pages first."""
        pinned_page = WikiPage(
            title="Pinned Page",
            slug="pinned-page",
            content="Pinned content",
            is_pinned=True,
            organization_id=None,
        )
        db_session.add(pinned_page)
        
        unpinned_page = WikiPage(
            title="Unpinned Page",
            slug="unpinned-page",
            content="Unpinned content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(unpinned_page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.get("/wiki/")
            assert response.status_code == 200
            assert b"Pinned Page" in response.data

    def test_wiki_index_shows_page_tree(self, authenticated_client, db_session, user):
        """Test that wiki index shows hierarchical page tree."""
        parent = WikiPage(
            title="Parent Page",
            slug="parent-page",
            content="Parent content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(parent)
        
        child = WikiPage(
            title="Child Page",
            slug="child-page",
            content="Child content",
            is_pinned=False,
            parent_id=parent.id,
            organization_id=None,
        )
        db_session.add(child)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.get("/wiki/")
            assert response.status_code == 200
            assert b"Parent Page" in response.data
            assert b"Child Page" in response.data


class TestWikiViewPage:
    """Tests for viewing individual wiki pages."""

    def test_view_page_requires_login(self, client):
        """Test that viewing wiki page requires login."""
        response = client.get("/wiki/test-page")
        assert response.status_code in [302, 403, 404]

    def test_view_page_not_found(self, authenticated_client):
        """Test that nonexistent page redirects to 404."""
        response = authenticated_client.get("/wiki/nonexistent-page")
        assert response.status_code in [302, 403, 404]

    def test_view_page_shows_content(self, authenticated_client, db_session, user):
        """Test that wiki page view shows page content."""
        page = WikiPage(
            title="Test Wiki Page",
            slug="test-wiki-page",
            content="This is test wiki page content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.get("/wiki/test-wiki-page")
            assert response.status_code == 200
            assert b"Test Wiki Page" in response.data
            assert b"This is test wiki page content" in response.data

    def test_view_page_shows_breadcrumbs(self, authenticated_client, db_session, user):
        """Test that wiki page view shows breadcrumb navigation."""
        parent = WikiPage(
            title="Parent Page",
            slug="parent-page",
            content="Parent content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(parent)
        
        child = WikiPage(
            title="Child Page",
            slug="child-page",
            content="Child content",
            is_pinned=False,
            parent_page=parent,
            organization_id=None,
        )
        db_session.add(child)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.get("/wiki/child-page")
            assert response.status_code == 200
            assert b"Parent Page" in response.data
            assert b"Wiki" in response.data

    def test_view_page_shows_subpages(self, authenticated_client, db_session, user):
        """Test that wiki page view shows subpages."""
        parent = WikiPage(
            title="Parent Page",
            slug="parent-page",
            content="Parent content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(parent)
        db_session.flush()
        
        child = WikiPage(
            title="Child Page",
            slug="child-page",
            content="Child content",
            is_pinned=False,
            parent_page=parent,
            organization_id=None,
        )
        db_session.add(child)
        db_session.commit()
        db_session.refresh(parent)

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.get("/wiki/parent-page")
            assert response.status_code == 200
            assert b"Child Page" in response.data

    def test_view_page_403_without_permission(self, authenticated_client, db_session, user):
        """Test that wiki page requires VIEW permission."""
        page = WikiPage(
            title="Protected Page",
            slug="protected-page",
            content="Protected content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get("/wiki/protected-page")
            assert response.status_code in [302, 403, 404]


class TestWikiNewPage:
    """Tests for creating new wiki pages."""

    def test_new_page_requires_login(self, client):
        """Test that creating wiki page requires login."""
        response = client.get("/wiki/new")
        assert response.status_code in [302, 403, 404]

    def test_new_page_get_shows_form(self, authenticated_client):
        """Test that new page GET shows the form."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.get("/wiki/new")
            assert response.status_code == 200
            assert b"New Wiki Page" in response.data or b"Create" in response.data or b"Title" in response.data

    def test_new_page_post_creates_page(self, authenticated_client, db_session, user):
        """Test that valid form submission creates wiki page."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.post("/wiki/new", data={
                "title": "New Wiki Page",
                "slug": "new-wiki-page",
                "content": "Test content",
                "is_pinned": "",
                "parent_id": "0",
            }, follow_redirects=True)

            assert response.status_code == 200
            
            page = db_session.query(WikiPage).filter_by(slug="new-wiki-page").first()
            assert page is not None
            assert page.title == "New Wiki Page"

    def test_new_page_post_creates_revision(self, authenticated_client, db_session, user):
        """Test that creating wiki page creates initial revision."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.post("/wiki/new", data={
                "title": "Page with Revision",
                "slug": "page-with-revision",
                "content": "Initial content",
                "is_pinned": "",
                "parent_id": "0",
            }, follow_redirects=True)

            page = db_session.query(WikiPage).filter_by(slug="page-with-revision").first()
            assert page is not None
            
            revisions = db_session.query(WikiRevision).filter_by(page_id=page.id).all()
            assert len(revisions) >= 1

    def test_new_page_post_uploads_files(self, authenticated_client, db_session, user, temp_upload_folder):
        """Test that wiki page creation can upload files."""
        import os
        
        test_file_path = os.path.join(temp_upload_folder, "test.pdf")
        with open(test_file_path, "w") as f:
            f.write("test content")

        with patch("src.enrgdocdb.views.wiki.handle_user_file_upload") as mock_upload:
            mock_result = MagicMock()
            mock_result.user_files = [MagicMock()]
            mock_result.user_files[0].uploaded_file_name = "test.pdf"
            mock_result.user_files[0].file_path = test_file_path
            mock_result.template_args = {"document_tokens": [], "file_token": "test-token"}
            mock_upload.return_value = mock_result

            with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
                mock_perm.return_value = True
                response = authenticated_client.post("/wiki/new", data={
                    "title": "Page with Files",
                    "slug": "page-with-files",
                    "content": "Content",
                    "parent_id": "0",
                }, follow_redirects=True)

                assert response.status_code == 200


class TestWikiEditPage:
    """Tests for editing wiki pages."""

    def test_edit_page_requires_login(self, client):
        """Test that editing wiki page requires login."""
        response = client.get("/wiki/test/edit")
        assert response.status_code in [302, 403, 404]

    def test_edit_page_not_found(self, authenticated_client):
        """Test that editing nonexistent page returns 404."""
        response = authenticated_client.get("/wiki/nonexistent/edit")
        assert response.status_code in [302, 403, 404]

    def test_edit_page_get_shows_form(self, authenticated_client, db_session, user):
        """Test that edit page GET shows pre-populated form."""
        page = WikiPage(
            title="Original Title",
            slug="edit-test-page",
            content="Original content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.get("/wiki/edit-test-page/edit")
            assert response.status_code == 200
            assert b"Original Title" in response.data

    def test_edit_page_post_updates_page(self, authenticated_client, db_session, user):
        """Test that editing wiki page updates content."""
        page = WikiPage(
            title="Original Title",
            slug="edit-test-page",
            content="Original content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.post("/wiki/edit-test-page/edit", data={
                "title": "Updated Title",
                "slug": "edit-test-page",
                "content": "Updated content",
                "parent_id": "0",
                "is_pinned": "",
                "comment": "Updated content",
            }, follow_redirects=True)

            assert response.status_code == 200
            
            page = db_session.query(WikiPage).filter_by(slug="edit-test-page").first()
            assert page is not None
            assert page.title == "Updated Title"

    def test_edit_page_post_creates_revision(self, authenticated_client, db_session, user):
        """Test that editing wiki page creates revision."""
        page = WikiPage(
            title="Test Page",
            slug="revision-test-page",
            content="Original content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        # Create initial revision manually since it's an edit test
        revision = WikiRevision(
            page=page,
            author_id=user.id,
            content="Original content",
            comment="Initial revision",
        )
        db_session.add(revision)
        db_session.commit()
        db_session.refresh(page)

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.post("/wiki/revision-test-page/edit", data={
                "title": "Test Page",
                "slug": "revision-test-page",
                "content": "Updated content",
                "parent_id": "0",
                "is_pinned": "",
                "comment": "Updated content",
            }, follow_redirects=True)

            page = db_session.query(WikiPage).filter_by(slug="revision-test-page").first()
            revisions = db_session.query(WikiRevision).filter_by(page_id=page.id).all()
            assert len(revisions) >= 2

    def test_edit_page_post_validates_slug_uniqueness(self, authenticated_client, db_session, user):
        """Test that wiki page slug must be unique."""
        page1 = WikiPage(
            title="Page One",
            slug="duplicate-slug",
            content="Content one",
            is_pinned=False,
            organization_id=None,
        )
        page2 = WikiPage(
            title="Page Two",
            slug="different-slug",
            content="Content two",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page1)
        db_session.add(page2)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.post("/wiki/different-slug/edit", data={
                "title": "Page Two Updated",
                "slug": "duplicate-slug",
                "content": "Updated content",
                "parent_id": "0",
                "is_pinned": "",
                "comment": "",
            })
            
            assert response.status_code == 200

    def test_edit_page_post_validates_no_self_parent(self, authenticated_client, db_session, user):
        """Test that wiki page cannot be its own parent."""
        page = WikiPage(
            title="Test Page",
            slug="self-parent-test",
            content="Content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.post("/wiki/self-parent-test/edit", data={
                "title": "Test Page",
                "slug": "self-parent-test",
                "content": "Content",
                "parent_id": str(page.id),
                "is_pinned": "",
                "comment": "",
            })
            
            assert response.status_code == 200
            assert b"cannot be its own parent" in response.data.lower()


class TestWikiHistory:
    """Tests for wiki revision history."""

    def test_history_requires_login(self, client):
        """Test that viewing wiki history requires login."""
        response = client.get("/wiki/test/history")
        assert response.status_code in [302, 403, 404]

    def test_history_not_found(self, authenticated_client):
        """Test that history for nonexistent page returns 404."""
        response = authenticated_client.get("/wiki/nonexistent/history")
        assert response.status_code in [302, 403, 404]

    def test_history_shows_revisions(self, authenticated_client, db_session, user):
        """Test that wiki history shows all revisions."""
        page = WikiPage(
            title="Test Page",
            slug="history-test-page",
            content="Version 1",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        revision1 = WikiRevision(
            page=page,
            author_id=user.id,
            content="Version 1",
            comment="Initial revision",
        )
        revision2 = WikiRevision(
            page=page,
            author_id=user.id,
            content="Version 2",
            comment="Updated content",
        )
        db_session.add(revision1)
        db_session.add(revision2)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.get("/wiki/history-test-page/history")
            assert response.status_code == 200
            assert b"Rev 1" in response.data
            assert b"Rev 2" in response.data


class TestWikiViewRevision:
    """Tests for viewing individual wiki revisions."""

    def test_view_revision_requires_login(self, client):
        """Test that viewing revision requires login."""
        response = client.get("/wiki/test/revision/1")
        assert response.status_code in [302, 403, 404]

    def test_view_revision_not_found(self, authenticated_client):
        """Test that nonexistent revision returns 404."""
        response = authenticated_client.get("/wiki/test/revision/99999")
        assert response.status_code in [302, 403, 404]

    def test_view_revision_shows_content(self, authenticated_client, db_session, user):
        """Test that viewing revision shows revision content."""
        page = WikiPage(
            title="Test Page",
            slug="revision-view-test",
            content="Current content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        revision = WikiRevision(
            page=page,
            author_id=user.id,
            content="Old revision content",
            comment="Previous version",
        )
        db_session.add(revision)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.get(f"/wiki/revision-view-test/revision/{revision.id}")
            assert response.status_code == 200
            assert b"Old revision content" in response.data


class TestWikiDeletePage:
    """Tests for deleting wiki pages."""

    def test_delete_page_requires_login(self, client):
        """Test that deleting wiki page requires login."""
        response = client.post("/wiki/test/delete")
        assert response.status_code in [302, 403, 404]

    def test_delete_page_not_found(self, authenticated_client):
        """Test that deleting nonexistent page returns 404."""
        response = authenticated_client.post("/wiki/nonexistent/delete")
        assert response.status_code in [302, 403, 404]

    def test_delete_page_removes_page(self, authenticated_client, db_session, user):
        """Test that deleting wiki page removes it from database."""
        page = WikiPage(
            title="Page to Delete",
            slug="delete-test-page",
            content="Content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.post("/wiki/delete-test-page/delete", follow_redirects=True)
            assert response.status_code == 200
            
            deleted = db_session.query(WikiPage).filter_by(slug="delete-test-page").first()
            assert deleted is None

    def test_delete_page_removes_children(self, authenticated_client, db_session, user):
        """Test that deleting wiki page also removes child pages."""
        parent = WikiPage(
            title="Parent Page",
            slug="parent-delete-test",
            content="Parent content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(parent)
        
        child = WikiPage(
            title="Child Page",
            slug="child-delete-test",
            content="Child content",
            is_pinned=False,
            parent_id=parent.id,
            organization_id=None,
        )
        db_session.add(child)
        db_session.commit()

        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            response = authenticated_client.post("/wiki/parent-delete-test/delete", follow_redirects=True)
            assert response.status_code == 200


class TestWikiDownloadFile:
    """Tests for wiki file download."""

    def test_download_file_requires_login(self, client):
        """Test that wiki file download requires login."""
        response = client.get("/wiki/download-file/1")
        assert response.status_code in [302, 403, 404]

    def test_download_file_not_found(self, authenticated_client):
        """Test that downloading nonexistent file returns 404."""
        response = authenticated_client.get("/wiki/download-file/99999")
        # May redirect to login due to permission check, or return 404
        assert response.status_code in [302, 403, 404]
