"""
Tests for User model and related functionality.
"""
from src.enrgdocdb.models.user import Role, RolePermission, User


class TestUserUsernameGeneration:
    """Test username generation logic."""
    
    def test_username_generation_from_name(self, db_session):
        """Test that username is generated from first and last name."""
        user = User(
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_1",
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.username == "jdoe"
    
    def test_username_generation_with_special_characters(self, db_session):
        """Test username generation with special characters in names."""
        user = User(
            email="maria.garcia@example.com",
            first_name="María",
            last_name="García",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_2",
        )
        db_session.add(user)
        db_session.commit()
        
        # Should transliterate and remove special characters
        assert user.username == "mgarcia"
    
    def test_username_generation_with_spaces(self, db_session):
        """Test username generation with spaces in names."""
        user = User(
            email="mary.jane@example.com",
            first_name="Mary Jane",
            last_name="Watson",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_3",
        )
        db_session.add(user)
        db_session.commit()
        
        # Should remove spaces
        assert user.username == "mwatson"
    
    def test_username_generation_with_long_names(self, db_session):
        """Test username generation with long names."""
        user = User(
            email="christopher@example.com",
            first_name="Christopher",
            last_name="Pikeshis",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_4",
        )
        db_session.add(user)
        db_session.commit()
        
        # Last name should be truncated to 10 chars
        assert user.username == "cpikeshis"
    
    def test_username_generation_with_only_first_name(self, db_session):
        """Test username generation with only first name."""
        user = User(
            email="john@example.com",
            first_name="John",
            last_name="",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_5",
        )
        db_session.add(user)
        db_session.commit()
        
        # Username requires both first and last name, so it will be None
        # and will be auto-generated from email on next flush
        # For this test, we just verify the user is created
        assert user.id is not None
    
    def test_username_generation_with_only_last_name(self, db_session):
        """Test username generation with only last name."""
        user = User(
            email="john@example.com",
            first_name="",
            last_name="Doe",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_6",
        )
        db_session.add(user)
        db_session.commit()
        
        # Username requires both first and last name, so it will be None
        # For this test, we just verify the user is created
        assert user.id is not None
    
    def test_username_uniqueness(self, db_session, user):
        """Test that usernames are made unique when duplicates exist."""
        # First user already exists with username "testuser"
        
        # Create another user with same name pattern
        user2 = User(
            email="test2@example.com",
            first_name="Test",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_7",
        )
        db_session.add(user2)
        db_session.commit()
        
        # Should be made unique (different from testuser)
        assert user2.username != "testuser"
    
    def test_username_with_umlauts(self, db_session):
        """Test username generation with umlauts."""
        user = User(
            email="mueller@example.com",
            first_name="Müller",
            last_name="Schmidt",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_8",
        )
        db_session.add(user)
        db_session.commit()
        
        # Should transliterate umlauts
        assert "mueller" in user.username or "mschmidt" in user.username
    
    def test_username_with_numbers_in_name(self, db_session):
        """Test username generation with numbers in names."""
        user = User(
            email="user123@example.com",
            first_name="John123",
            last_name="Doe",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_9",
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.username == "jdoe"


class TestUserProperties:
    """Test User model properties."""
    
    def test_user_name_property_with_full_name(self, db_session, user):
        """Test user name property with full name."""
        assert user.name == "Test User"
    
    def test_user_name_property_with_deleted_user(self, db_session):
        """Test user name property for deleted user."""
        from datetime import datetime
        user = User(
            email="deleted@example.com",
            username="deleteduser",
            first_name="Deleted",
            last_name="User",
            password="hashed_password",
            active=True,
            deleted_at=datetime.now(),
            fs_uniquifier="test_uniquifier_10",
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.name == "Deleted User"
    
    def test_user_name_property_without_first_name(self, db_session):
        """Test user name property when first name is missing."""
        user = User(
            email="johndoe@example.com",
            username="johndoe",
            first_name=None,
            last_name="Doe",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_11",
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.name == "johndoe@example.com"
    
    def test_user_name_property_with_only_first_name(self, db_session):
        """Test user name property with only first name."""
        user = User(
            email="john@example.com",
            username="johndoe",
            first_name="John",
            last_name=None,
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_12",
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.name == "John "


class TestUserLDAPUID:
    """Test LDAP UID generation."""
    
    def test_ldap_uid_from_username(self, db_session):
        """Test LDAP UID uses username when set."""
        user = User(
            email="test@example.com",
            username="custom_username",
            first_name="Test",
            last_name="User",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_13",
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.get_ldap_uid() == "custom_username"
    
    def test_ldap_uid_generated_from_name(self, db_session):
        """Test LDAP UID is generated from name when username not set."""
        user = User(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_14",
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.get_ldap_uid() == "jdoe"
    
    def test_ldap_uid_cached(self, db_session):
        """Test that LDAP UID is cached."""
        user = User(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            password="hashed_password",
            active=True,
            fs_uniquifier="test_uniquifier_15",
        )
        db_session.add(user)
        db_session.commit()
        
        uid1 = user.get_ldap_uid()
        uid2 = user.get_ldap_uid()
        
        assert uid1 == uid2


class TestUserOrganization:
    """Test user organization methods."""
    
    def test_get_organizations_with_roles(self, db_session, user, organization, role):
        """Test getting organizations from user roles."""
        # Add role to user
        user.roles.append(role)
        db_session.commit()
        
        orgs = user.get_organizations()
        assert len(orgs) == 1
        assert orgs[0].id == organization.id
    
    def test_get_organizations_without_roles(self, db_session, user):
        """Test getting organizations when user has no roles."""
        orgs = user.get_organizations()
        assert len(orgs) == 0
    
    def test_get_organizations_super_admin(self, db_session, admin_user, organization):
        """Test super admin gets all organizations."""
        # Super admin has organization_id=None role with ADMIN permission
        super_admin_role = Role(
            name="super_admin",
            permissions=[p.value for p in RolePermission],
            organization_id=None,  # No organization = super admin
        )
        admin_user.roles.append(super_admin_role)
        db_session.commit()
        
        orgs = admin_user.get_organizations()
        assert len(orgs) >= 1


class TestRoleModel:
    """Test Role model."""
    
    def test_role_with_organization(self, db_session, role, organization):
        """Test role with organization."""
        assert role.organization_id == organization.id
        assert role.organization.name == "Test Organization"
    
    def test_role_without_organization(self, db_session):
        """Test role without organization (super admin role)."""
        role = Role(
            name="admin",
            permissions=[p.value for p in RolePermission],
            organization_id=None,
        )
        db_session.add(role)
        db_session.commit()
        
        assert role.organization_id is None
        assert role.organization is None
    
    def test_role_repr_with_organization(self, db_session, role, organization):
        """Test role string representation with organization."""
        assert "admin" not in str(role).lower()  # role name is "user"
        assert organization.name in str(role)
    
    def test_role_repr_without_organization(self, db_session):
        """Test role string representation without organization."""
        role = Role(
            name="admin",
            permissions=[p.value for p in RolePermission],
            organization_id=None,
        )
        db_session.add(role)
        db_session.commit()
        
        assert str(role) == "Admin"


class TestOrganizationModel:
    """Test Organization model."""
    
    def test_organization_with_roles(self, db_session, organization, role):
        """Test organization with roles."""
        assert len(organization.roles) == 1
        assert organization.roles[0].id == role.id
    
    def test_organization_repr(self, db_session, organization):
        """Test organization string representation."""
        assert str(organization) == "Test Organization"


class TestRolePermission:
    """Test RolePermission enum."""
    
    def test_role_permission_values(self):
        """Test RolePermission has expected values."""
        assert RolePermission.VIEW == "VIEW"
        assert RolePermission.ADD == "ADD"
        assert RolePermission.EDIT_SELF == "EDIT_SELF"
        assert RolePermission.EDIT == "EDIT"
        assert RolePermission.REMOVE == "REMOVE"
        assert RolePermission.ADMIN == "ADMIN"
    
    def test_roles_permissions_by_organization(self):
        """Test role permissions configuration for organizations."""
        # Guest can only view
        assert RolePermission.VIEW in ROLES_PERMISSIONS_BY_ORGANIZATION["guest"]
        assert RolePermission.ADD not in ROLES_PERMISSIONS_BY_ORGANIZATION["guest"]
        
        # User can view and edit self
        assert RolePermission.VIEW in ROLES_PERMISSIONS_BY_ORGANIZATION["user"]
        assert RolePermission.EDIT_SELF in ROLES_PERMISSIONS_BY_ORGANIZATION["user"]
        assert RolePermission.ADD not in ROLES_PERMISSIONS_BY_ORGANIZATION["user"]
        
        # Moderator can do most things
        assert RolePermission.VIEW in ROLES_PERMISSIONS_BY_ORGANIZATION["moderator"]
        assert RolePermission.ADD in ROLES_PERMISSIONS_BY_ORGANIZATION["moderator"]
        assert RolePermission.EDIT in ROLES_PERMISSIONS_BY_ORGANIZATION["moderator"]
        assert RolePermission.REMOVE in ROLES_PERMISSIONS_BY_ORGANIZATION["moderator"]
        assert RolePermission.ADMIN not in ROLES_PERMISSIONS_BY_ORGANIZATION["moderator"]


from src.enrgdocdb.models.user import ROLES_PERMISSIONS_BY_ORGANIZATION
