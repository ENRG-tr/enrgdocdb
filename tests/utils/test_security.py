"""
Tests for security utilities and permission checking.
"""
from unittest.mock import MagicMock

from src.enrgdocdb.models.user import RolePermission, User, Role, Organization
from src.enrgdocdb.models.document import Document, DocumentType
from src.enrgdocdb.models.author import Author


class TestRolesHavePermission:
    """Test _roles_have_permission function."""
    
    def test_role_has_permission(self, db_session):
        """Test that role with permission returns True."""
        from src.enrgdocdb.utils.security import _roles_have_permission
        
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_1",
        )
        org = Organization(name="Test Organization")
        role = Role(
            name="user",
            permissions=[RolePermission.VIEW, RolePermission.EDIT_SELF],
            organization_id=org.id,
        )
        db_session.add_all([user, org, role])
        db_session.commit()
        user.roles.append(role)
        db_session.commit()
        
        # User should have VIEW permission
        assert _roles_have_permission(user, org.id, RolePermission.VIEW) is True
    
    def test_role_without_permission(self, db_session):
        """Test that role without permission returns False."""
        from src.enrgdocdb.utils.security import _roles_have_permission
        
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_2",
        )
        org = Organization(name="Test Organization")
        role = Role(
            name="user",
            permissions=[RolePermission.VIEW],
            organization_id=org.id,
        )
        db_session.add_all([user, org, role])
        db_session.commit()
        user.roles.append(role)
        db_session.commit()
        
        # User should NOT have ADD permission
        assert _roles_have_permission(user, org.id, RolePermission.ADD) is False
    
    def test_role_different_organization(self, db_session):
        """Test permission check across different organizations."""
        from src.enrgdocdb.utils.security import _roles_have_permission
        
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_3",
        )
        org1 = Organization(name="Org 1")
        org2 = Organization(name="Org 2")
        db_session.add_all([user, org1, org2])
        db_session.commit()
        
        role = Role(
            name="user",
            permissions=[RolePermission.VIEW, RolePermission.ADD],
            organization_id=org1.id,
        )
        db_session.add(role)
        db_session.commit()
        user.roles.append(role)
        db_session.commit()
        
        # User has permission for org1
        assert _roles_have_permission(user, org1.id, RolePermission.VIEW) is True
        
        # User does NOT have permission for org2
        assert _roles_have_permission(user, org2.id, RolePermission.VIEW) is False
    
    def test_role_no_organization(self, db_session):
        """Test permission check for role without organization."""
        from src.enrgdocdb.utils.security import _roles_have_permission
        
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_4",
        )
        db_session.add(user)
        db_session.commit()
        
        role = Role(
            name="admin",
            permissions=[RolePermission.VIEW, RolePermission.ADD],
            organization_id=None,  # No organization = all organizations
        )
        db_session.add(role)
        db_session.commit()
        user.roles.append(role)
        db_session.commit()
        
        # User with no organization role has access to all organizations
        assert _roles_have_permission(user, 123, RolePermission.VIEW) is True


class TestIsSuperAdmin:
    """Test _is_super_admin function."""
    
    def test_is_super_admin(self, db_session):
        """Test that super admin is recognized."""
        from src.enrgdocdb.utils.security import _is_super_admin
        
        user = User(
            email="admin@example.com",
            username="adminuser",
            first_name="Admin",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_5",
        )
        super_admin_role = Role(
            name="super_admin",
            permissions=[p.value for p in RolePermission],
            organization_id=None,  # No organization = super admin
        )
        db_session.add_all([user, super_admin_role])
        db_session.commit()
        user.roles.append(super_admin_role)
        db_session.commit()
        
        assert _is_super_admin(user) is True
    
    def test_not_super_admin(self, db_session):
        """Test that regular admin is not recognized as super admin."""
        from src.enrgdocdb.utils.security import _is_super_admin
        
        user = User(
            email="admin@example.com",
            username="adminuser",
            first_name="Admin",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_6",
        )
        org = Organization(name="Test Organization")
        db_session.add_all([user, org])
        db_session.commit()
        
        admin_role = Role(
            name="admin",
            permissions=[RolePermission.VIEW, RolePermission.ADMIN],
            organization_id=org.id,
        )
        db_session.add(admin_role)
        db_session.commit()
        user.roles.append(admin_role)
        db_session.commit()
        
        assert _is_super_admin(user) is False
    
    def test_not_super_admin_no_admin_permission(self, db_session):
        """Test that user without admin permission is not super admin."""
        from src.enrgdocdb.utils.security import _is_super_admin
        
        user = User(
            email="user@example.com",
            username="user",
            first_name="User",
            last_name="Name",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_7",
        )
        role = Role(
            name="user",
            permissions=[RolePermission.VIEW, RolePermission.EDIT_SELF],
            organization_id=None,
        )
        db_session.add_all([user, role])
        db_session.commit()
        user.roles.append(role)
        db_session.commit()
        
        assert _is_super_admin(user) is False


class TestPermissionCheckDocument:
    """Test permission_check with Document model."""
    
    def test_permission_check_document_view(self, db_session, document, user, organization, role):
        """Test permission check for viewing document."""
        from src.enrgdocdb.utils.security import permission_check
        
        # Add user role with VIEW permission
        db_session.add_all([organization, role])
        db_session.commit()
        user.roles.append(role)
        db_session.commit()
        
        # Mock current_user and limiter
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.roles = user.roles
        mock_user.id = user.id
        
        with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.current_user', mock_user):
            with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.limiter'):
                assert permission_check(document, RolePermission.VIEW) is True
    
    def test_permission_check_document_edit(self, db_session, document, user, organization):
        """Test permission check for editing document."""
        from src.enrgdocdb.utils.security import permission_check
        
        # User is the document owner, should have EDIT permission via EDIT_SELF
        role = Role(
            name="user",
            permissions=[RolePermission.VIEW, RolePermission.EDIT_SELF],
            organization_id=organization.id,
        )
        db_session.add(role)
        db_session.commit()
        user.roles.append(role)
        db_session.commit()
        
        # Mock current_user and limiter
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.roles = user.roles
        mock_user.id = user.id
        
        with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.current_user', mock_user):
            with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.limiter'):
                assert permission_check(document, RolePermission.EDIT) is True
    
    def test_permission_check_document_edit_with_edit_permission(self, db_session, document, user, organization):
        """Test permission check for editing document with EDIT permission."""
        from src.enrgdocdb.utils.security import permission_check
        
        # Create a new user who owns the document
        document_owner = User(
            email="owner@example.com",
            username="owneruser",
            first_name="Owner",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_owner",
        )
        db_session.add(document_owner)
        db_session.commit()
        
        # Update document to be owned by this user
        document.user_id = document_owner.id
        db_session.commit()
        
        # Add EDIT permission role to document owner
        role = Role(
            name="moderator",
            permissions=[RolePermission.VIEW, RolePermission.EDIT, RolePermission.EDIT_SELF],
            organization_id=organization.id,
        )
        db_session.add(role)
        db_session.commit()
        document_owner.roles.append(role)
        db_session.commit()
        
        # Mock current_user and limiter
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.roles = document_owner.roles
        mock_user.id = document_owner.id
        
        with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.current_user', mock_user):
            with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.limiter'):
                assert permission_check(document, RolePermission.EDIT) is True
    def test_permission_check_document_add(self, db_session, document, user, organization):
        """Test permission check for adding to document."""
        from src.enrgdocdb.utils.security import permission_check

        # Clear existing roles to test ADD permission specifically
        user.roles.clear()
        db_session.commit()

        role = Role(
            name="user_no_add",
            permissions=[RolePermission.VIEW, RolePermission.EDIT_SELF],
            organization_id=organization.id,
        )
        db_session.add(role)
        db_session.commit()

        user.roles.append(role)
        db_session.commit()

        # Mock current_user and limiter
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.roles = user.roles
        mock_user.id = user.id

        with __import__("unittest").mock.patch(
            "src.enrgdocdb.utils.security.current_user", mock_user
        ):
            with __import__("unittest").mock.patch(
                "src.enrgdocdb.utils.security.limiter"
            ):
                # User should not have ADD permission
                assert permission_check(document, RolePermission.ADD) is False


class TestPermissionCheckAuthor:
    """Test permission_check with Author model."""
    
    def test_permission_check_author_add(self, db_session, author):
        """Test permission check for adding authors (always allowed)."""
        from src.enrgdocdb.utils.security import permission_check
        
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_8",
        )
        
        # Mock current_user and limiter
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.roles = []
        mock_user.id = user.id
        
        with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.current_user', mock_user):
            with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.limiter'):
                # Adding authors is always allowed (checks if model is Author class)
                assert permission_check(Author, RolePermission.ADD) is True


class TestPermissionCheckUnauthenticated:
    """Test permission_check with unauthenticated user."""
    
    def test_unauthenticated_user_no_permissions(self):
        """Test that unauthenticated user has no permissions."""
        from src.enrgdocdb.utils.security import permission_check
        
        # Mock unauthenticated user
        mock_user = MagicMock()
        mock_user.is_authenticated = False
        
        with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.current_user', mock_user):
            assert permission_check(None, RolePermission.VIEW) is False


class TestPermissionCheckSuperAdmin:
    """Test permission_check with super admin user."""
    
    def test_super_admin_all_permissions(self, db_session):
        """Test that super admin has all permissions."""
        from src.enrgdocdb.utils.security import permission_check
        
        super_admin = User(
            email="superadmin@example.com",
            username="superadmin",
            first_name="Super",
            last_name="Admin",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_9",
        )
        super_admin_role = Role(
            name="super_admin",
            permissions=[p.value for p in RolePermission],
            organization_id=None,
        )
        db_session.add_all([super_admin, super_admin_role])
        db_session.commit()
        super_admin.roles.append(super_admin_role)
        db_session.commit()
        
        # Create a document
        doc_type = DocumentType(name="Conference Paper")
        document = Document(
            title="Test Document",
            document_type=doc_type,
            user_id=1,
            organization_id=1,
        )
        db_session.add_all([doc_type, document])
        db_session.commit()
        
        # Mock current_user and limiter
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.roles = super_admin.roles
        mock_user.id = super_admin.id
        
        with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.current_user', mock_user):
            with __import__('unittest').mock.patch('src.enrgdocdb.utils.security.limiter'):
                # Super admin should have all permissions
                assert permission_check(document, RolePermission.VIEW) is True
                assert permission_check(document, RolePermission.ADD) is True
                assert permission_check(document, RolePermission.EDIT) is True
                assert permission_check(document, RolePermission.REMOVE) is True
                assert permission_check(document, RolePermission.ADMIN) is True
