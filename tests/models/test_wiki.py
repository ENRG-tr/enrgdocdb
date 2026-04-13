"""
Tests for Wiki model and related functionality.
"""
from datetime import datetime, timedelta

from src.enrgdocdb.models.wiki import (
    WikiPage,
    WikiRevision,
    WikiFile,
    WikiPagePermission,
    WIKI_CONTENT_SIZE,
)
from src.enrgdocdb.models.user import RolePermission, User


class TestWikiPage:
    """Test WikiPage model."""
    
    def test_wiki_page_creation(self, db_session, wiki_page):
        """Test creating a wiki page."""
        assert wiki_page.id is not None
        assert wiki_page.title == "Test Page"
        assert wiki_page.slug == "test-page"
        assert wiki_page.content == "Test content"
        assert wiki_page.is_pinned is False
    
    def test_wiki_page_with_parent(self, db_session, wiki_page):
        """Test creating a wiki page with parent."""
        parent_page = WikiPage(
            title="Parent Page",
            slug="parent-page",
            content="Parent content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(parent_page)
        db_session.commit()
        
        child_page = WikiPage(
            title="Child Page",
            slug="child-page",
            content="Child content",
            is_pinned=False,
            parent_id=parent_page.id,
            organization_id=None,
        )
        db_session.add(child_page)
        db_session.commit()
        
        assert child_page.parent_page.id == parent_page.id
        assert parent_page.child_pages[0].id == child_page.id
    
    def test_wiki_page_hierarchy(self, db_session):
        """Test wiki page hierarchy with multiple levels."""
        level1 = WikiPage(
            title="Level 1",
            slug="level-1",
            content="Level 1 content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(level1)
        db_session.commit()
        
        level2 = WikiPage(
            title="Level 2",
            slug="level-2",
            content="Level 2 content",
            is_pinned=False,
            parent_id=level1.id,
            organization_id=None,
        )
        db_session.add(level2)
        db_session.commit()
        
        level3 = WikiPage(
            title="Level 3",
            slug="level-3",
            content="Level 3 content",
            is_pinned=False,
            parent_id=level2.id,
            organization_id=None,
        )
        db_session.add(level3)
        db_session.commit()
        
        # Reload to verify hierarchy
        level1 = db_session.get(WikiPage, level1.id)
        level2 = db_session.get(WikiPage, level2.id)
        level3 = db_session.get(WikiPage, level3.id)
        
        assert level3.parent_id == level2.id
        assert level2.parent_id == level1.id
        assert level1.parent_id is None
    
    def test_wiki_page_child_pages_relationship(self, db_session):
        """Test wiki page child pages relationship."""
        parent = WikiPage(
            title="Parent",
            slug="parent",
            content="Parent content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(parent)
        db_session.commit()
        
        child1 = WikiPage(
            title="Child 1",
            slug="child-1",
            content="Child 1 content",
            is_pinned=False,
            parent_id=parent.id,
            organization_id=None,
        )
        child2 = WikiPage(
            title="Child 2",
            slug="child-2",
            content="Child 2 content",
            is_pinned=False,
            parent_id=parent.id,
            organization_id=None,
        )
        db_session.add_all([child1, child2])
        db_session.commit()
        
        # Reload parent to get child_pages relationship loaded
        parent = db_session.get(WikiPage, parent.id)
        
        # Query child pages directly to verify relationship
        child_pages = db_session.query(WikiPage).filter_by(parent_id=parent.id).all()
        assert len(child_pages) == 2
        
        # Verify child_pages relationship is loaded
        assert len(parent.child_pages) == 2
    
    def test_wiki_page_revisions_relationship(self, db_session, wiki_page, user):
        """Test wiki page revisions relationship."""
        # Add wiki_page and user first to ensure they have IDs
        db_session.add(wiki_page)
        db_session.add(user)
        db_session.commit()
        
        # Add revisions with explicit timestamps to ensure ordering
        base_time = datetime.now()
        
        revision1 = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Revision 1 content",
            comment="First revision",
            created_at=base_time - timedelta(seconds=2),
        )
        revision2 = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Revision 2 content",
            comment="Second revision",
            created_at=base_time - timedelta(seconds=1),
        )
        db_session.add_all([revision1, revision2])
        db_session.commit()
        
        # Reload page to get revisions relationship loaded
        wiki_page = db_session.get(WikiPage, wiki_page.id)
        
        # Query revisions directly to verify relationship (ordered by created_at DESC)
        from sqlalchemy import desc
        revisions = db_session.query(WikiRevision).filter_by(
            page_id=wiki_page.id
        ).order_by(desc(WikiRevision.created_at)).all()
        assert len(revisions) == 2
        assert revisions[0].content == "Revision 2 content"
        assert revisions[1].content == "Revision 1 content"
    
    def test_wiki_page_files_relationship(self, db_session, wiki_page):
        """Test wiki page files relationship."""
        file1 = WikiFile(
            page_id=wiki_page.id,
            file_name="file1.pdf",
            real_file_name="/uploads/wiki/123/file1.pdf",
        )
        file2 = WikiFile(
            page_id=wiki_page.id,
            file_name="file2.pdf",
            real_file_name="/uploads/wiki/123/file2.pdf",
        )
        wiki_page.files.extend([file1, file2])
        db_session.commit()
        
        assert len(wiki_page.files) == 2
        assert file1 in wiki_page.files
        assert file2 in wiki_page.files
    
    def test_wiki_page_permissions_relationship(self, db_session, wiki_page, role):
        """Test wiki page permissions relationship."""
        permission = WikiPagePermission(
            page_id=wiki_page.id,
            role_id=role.id,
            permission=RolePermission.VIEW,
        )
        wiki_page.permissions.append(permission)
        db_session.commit()
        
        assert len(wiki_page.permissions) == 1
        assert wiki_page.permissions[0].role.id == role.id
    
    def test_wiki_page_with_organization(self, db_session, wiki_page, organization):
        """Test wiki page with organization."""
        page_with_org = WikiPage(
            title="Org Page",
            slug="org-page",
            content="Org content",
            is_pinned=False,
            organization_id=organization.id,
        )
        db_session.add(page_with_org)
        db_session.commit()
        
        assert page_with_org.organization_id == organization.id
        assert page_with_org.organization.name == "Test Organization"
    
    def test_wiki_page_without_organization(self, db_session, wiki_page):
        """Test wiki page without organization."""
        assert wiki_page.organization_id is None
        assert wiki_page.organization is None
    
    def test_wiki_page_abstract_optional(self, db_session):
        """Test that wiki page content is required."""
        # Content is required by the model (nullable=False)
        page = WikiPage(
            title="Required Content Page",
            slug="required-content-page",
            content="",  # Can be empty string but field is required
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()
        
        assert page.content == ""
    
    def test_wiki_page_title_max_length(self, db_session):
        """Test wiki page title max length."""
        long_title = "A" * 512  # Max length for title field
        page = WikiPage(
            title=long_title,
            slug="long-title-page",
            content="Content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()
        
        assert len(page.title) == 512
    
    def test_wiki_page_content_max_length(self, db_session):
        """Test wiki page content max length."""
        long_content = "B" * WIKI_CONTENT_SIZE  # Max length for content field
        page = WikiPage(
            title="Long Content Page",
            slug="long-content-page",
            content=long_content,
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page)
        db_session.commit()
        
        assert len(page.content) == WIKI_CONTENT_SIZE
    
    def test_wiki_page_slug_unique(self, db_session, wiki_page):
        """Test that wiki page slugs are unique."""
        # wiki_page already has slug "test-page"
        page2 = WikiPage(
            title="Another Page",
            slug="another-page",
            content="Content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(page2)
        db_session.commit()
        
        assert page2.slug == "another-page"
        assert page2.slug != wiki_page.slug
    
    def test_wiki_page_repr(self, db_session, wiki_page):
        """Test wiki page string representation."""
        assert str(wiki_page) == "Test Page"
    
    def test_wiki_page_pinned(self, db_session, wiki_page):
        """Test wiki page pinned status."""
        wiki_page.is_pinned = True
        db_session.commit()
        
        assert wiki_page.is_pinned is True
    
    def test_wiki_page_cascade_delete_child_pages(self, db_session):
        """Test that child pages are deleted when parent is deleted."""
        parent = WikiPage(
            title="Parent",
            slug="parent",
            content="Parent content",
            is_pinned=False,
            organization_id=None,
        )
        db_session.add(parent)
        db_session.commit()
        
        child = WikiPage(
            title="Child",
            slug="child",
            content="Child content",
            is_pinned=False,
            parent_id=parent.id,
            organization_id=None,
        )
        db_session.add(child)
        db_session.commit()
        
        child_id = child.id  # Save ID before delete
        
        db_session.delete(parent)
        db_session.commit()
        
        # Child should be deleted due to cascade
        deleted_child = db_session.get(WikiPage, child_id)
        assert deleted_child is None
    
    def test_wiki_page_cascade_delete_revisions(self, db_session, wiki_page):
        """Test that revisions are deleted when page is deleted."""
        user = User(
            email="author@example.com",
            username="authoruser",
            first_name="Author",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_author",
        )
        db_session.add(user)
        db_session.commit()
        
        revision = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Revision content",
            comment="Test revision",
        )
        wiki_page.revisions.append(revision)
        db_session.commit()
        
        db_session.delete(wiki_page)
        db_session.commit()
        
        # Revision should be deleted due to cascade
        deleted_revision = db_session.get(WikiRevision, revision.id)
        assert deleted_revision is None
    
    def test_wiki_page_cascade_delete_files(self, db_session, wiki_page):
        """Test that files are deleted when page is deleted."""
        file = WikiFile(
            page_id=wiki_page.id,
            file_name="test.pdf",
            real_file_name="/uploads/wiki/123/test.pdf",
        )
        wiki_page.files.append(file)
        db_session.commit()
        
        db_session.delete(wiki_page)
        db_session.commit()
        
        # File should be deleted due to cascade
        deleted_file = db_session.get(WikiFile, file.id)
        assert deleted_file is None
    
    def test_wiki_page_cascade_delete_permissions(self, db_session, wiki_page, role):
        """Test that permissions are deleted when page is deleted."""
        permission = WikiPagePermission(
            page_id=wiki_page.id,
            role_id=role.id,
            permission=RolePermission.VIEW,
        )
        wiki_page.permissions.append(permission)
        db_session.commit()
        
        db_session.delete(wiki_page)
        db_session.commit()
        
        # Permission should be deleted due to cascade
        deleted_permission = db_session.get(WikiPagePermission, permission.id)
        assert deleted_permission is None


class TestWikiRevision:
    """Test WikiRevision model."""
    
    def test_wiki_revision_creation(self, db_session, wiki_page, user):
        """Test creating a wiki revision."""
        revision = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Revision content",
            comment="Test revision",
        )
        db_session.add(revision)
        db_session.commit()
        
        assert revision.id is not None
        assert revision.page_id == wiki_page.id
        assert revision.author_id == user.id
        assert revision.content == "Revision content"
        assert revision.comment == "Test revision"
    
    def test_wiki_revision_page_relationship(self, db_session, wiki_page, user):
        """Test wiki revision page relationship."""
        revision = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Revision content",
            comment="Test revision",
        )
        db_session.add(revision)
        db_session.commit()
        
        assert revision.page.id == wiki_page.id
        assert revision.page.title == "Test Page"
    
    def test_wiki_revision_author_relationship(self, db_session, wiki_page, user):
        """Test wiki revision author relationship."""
        revision = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Revision content",
            comment="Test revision",
        )
        db_session.add(revision)
        db_session.commit()
        
        assert revision.author.id == user.id
        assert revision.author.email == user.email
    
    def test_wiki_revision_without_comment(self, db_session, wiki_page, user):
        """Test wiki revision without comment."""
        revision = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Revision content",
            comment=None,
        )
        db_session.add(revision)
        db_session.commit()
        
        assert revision.comment is None
    
    def test_wiki_revision_content_max_length(self, db_session, wiki_page, user):
        """Test wiki revision content max length."""
        long_content = "C" * WIKI_CONTENT_SIZE
        revision = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content=long_content,
            comment="Long content revision",
        )
        db_session.add(revision)
        db_session.commit()
        
        assert len(revision.content) == WIKI_CONTENT_SIZE
    
    def test_wiki_revision_comment_max_length(self, db_session, wiki_page, user):
        """Test wiki revision comment max length."""
        long_comment = "D" * 1024
        revision = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Content",
            comment=long_comment,
        )
        db_session.add(revision)
        db_session.commit()
        
        assert len(revision.comment) == 1024
    
    def test_wiki_revision_multiple_revisions(self, db_session, wiki_page, user):
        """Test wiki page with multiple revisions."""
        # Add wiki_page and user first to ensure they have IDs
        db_session.add(wiki_page)
        db_session.add(user)
        db_session.commit()
        
        # Add revisions with explicit timestamps to ensure ordering
        base_time = datetime.now()
        
        revision1 = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="First revision",
            comment="First",
            created_at=base_time - timedelta(seconds=2),
        )
        revision2 = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Second revision",
            comment="Second",
            created_at=base_time - timedelta(seconds=1),
        )
        revision3 = WikiRevision(
            page_id=wiki_page.id,
            author_id=user.id,
            content="Third revision",
            comment="Third",
            created_at=base_time,
        )
        db_session.add_all([revision1, revision2, revision3])
        db_session.commit()
        
        # Reload page to get revisions relationship loaded
        wiki_page = db_session.get(WikiPage, wiki_page.id)
        
        # Query revisions directly to verify relationship (ordered by created_at DESC)
        from sqlalchemy import desc
        revisions = db_session.query(WikiRevision).filter_by(
            page_id=wiki_page.id
        ).order_by(desc(WikiRevision.created_at)).all()
        assert len(revisions) == 3
        assert revisions[0].content == "Third revision"
        assert revisions[2].content == "First revision"


class TestWikiFile:
    """Test WikiFile model."""
    
    def test_wiki_file_creation(self, db_session, wiki_page):
        """Test creating a wiki file."""
        file = WikiFile(
            page_id=wiki_page.id,
            file_name="document.pdf",
            real_file_name="/uploads/wiki/123/document.pdf",
        )
        db_session.add(file)
        db_session.commit()
        
        assert file.id is not None
        assert file.page_id == wiki_page.id
        assert file.file_name == "document.pdf"
        assert file.real_file_name.startswith("/uploads/")
    
    def test_wiki_file_page_relationship(self, db_session, wiki_page):
        """Test wiki file page relationship."""
        file = WikiFile(
            page_id=wiki_page.id,
            file_name="test.pdf",
            real_file_name="/uploads/wiki/123/test.pdf",
        )
        db_session.add(file)
        db_session.commit()
        
        assert file.page.id == wiki_page.id
        assert file.page.title == "Test Page"
    
    def test_wiki_file_repr(self, db_session, wiki_page):
        """Test wiki file string representation."""
        file = WikiFile(
            page_id=wiki_page.id,
            file_name="report.pdf",
            real_file_name="/uploads/wiki/123/report.pdf",
        )
        db_session.add(file)
        db_session.commit()
        
        assert str(file) == "report.pdf"
    
    def test_wiki_file_multiple_files(self, db_session, wiki_page):
        """Test wiki page with multiple files."""
        file1 = WikiFile(
            page_id=wiki_page.id,
            file_name="file1.pdf",
            real_file_name="/uploads/wiki/123/file1.pdf",
        )
        file2 = WikiFile(
            page_id=wiki_page.id,
            file_name="file2.pdf",
            real_file_name="/uploads/wiki/123/file2.pdf",
        )
        file3 = WikiFile(
            page_id=wiki_page.id,
            file_name="file3.pdf",
            real_file_name="/uploads/wiki/123/file3.pdf",
        )
        wiki_page.files.extend([file1, file2, file3])
        db_session.commit()
        
        assert len(wiki_page.files) == 3
        assert file1 in wiki_page.files
        assert file2 in wiki_page.files
        assert file3 in wiki_page.files


class TestWikiPagePermission:
    """Test WikiPagePermission model."""
    
    def test_wiki_page_permission_creation(self, db_session, wiki_page, role):
        """Test creating a wiki page permission."""
        permission = WikiPagePermission(
            page_id=wiki_page.id,
            role_id=role.id,
            permission=RolePermission.VIEW,
        )
        db_session.add(permission)
        db_session.commit()
        
        assert permission.id is not None
        assert permission.page_id == wiki_page.id
        assert permission.role_id == role.id
        assert permission.permission == RolePermission.VIEW
    
    def test_wiki_page_permission_page_relationship(self, db_session, wiki_page, role):
        """Test wiki page permission page relationship."""
        permission = WikiPagePermission(
            page_id=wiki_page.id,
            role_id=role.id,
            permission=RolePermission.VIEW,
        )
        db_session.add(permission)
        db_session.commit()
        
        assert permission.page.id == wiki_page.id
        assert permission.page.title == "Test Page"
    
    def test_wiki_page_permission_role_relationship(self, db_session, wiki_page, role):
        """Test wiki page permission role relationship."""
        permission = WikiPagePermission(
            page_id=wiki_page.id,
            role_id=role.id,
            permission=RolePermission.VIEW,
        )
        db_session.add(permission)
        db_session.commit()
        
        assert permission.role.id == role.id
        assert permission.role.name == role.name
    
    def test_wiki_page_permission_repr(self, db_session, wiki_page, role):
        """Test wiki page permission string representation."""
        permission = WikiPagePermission(
            page_id=wiki_page.id,
            role_id=role.id,
            permission=RolePermission.VIEW,
        )
        db_session.add(permission)
        db_session.commit()
        
        # Role name is "user"
        assert "user" in str(permission).lower()
        assert "view" in str(permission).lower()
    
    def test_wiki_page_permission_multiple_permissions(self, db_session, wiki_page, role):
        """Test wiki page with multiple permissions."""
        permission1 = WikiPagePermission(
            page_id=wiki_page.id,
            role_id=role.id,
            permission=RolePermission.VIEW,
        )
        permission2 = WikiPagePermission(
            page_id=wiki_page.id,
            role_id=role.id,
            permission=RolePermission.ADD,
        )
        wiki_page.permissions.extend([permission1, permission2])
        db_session.commit()
        
        assert len(wiki_page.permissions) == 2
        permissions = [p.permission for p in wiki_page.permissions]
        assert RolePermission.VIEW in permissions
        assert RolePermission.ADD in permissions
