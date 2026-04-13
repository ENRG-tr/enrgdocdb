"""
View tests for User profile operations.

Tests user profile viewing, editing, creation, and permission enforcement.
"""
from unittest.mock import patch

from src.enrgdocdb.models.user import User


class TestUserProfileView:
    """Tests for viewing user profiles."""

    def test_view_profile_requires_authentication(self, client):
        """Test that viewing a profile requires authentication."""
        response = client.get("/user/view/1")
        assert response.status_code in [302, 403, 404]

    def test_view_profile_404_for_nonexistent(self, authenticated_client):
        """Test that viewing nonexistent profile returns 404."""
        response = authenticated_client.get("/user/view/99999")
        assert response.status_code == 404

    def test_view_profile_shows_user_info(self, authenticated_client, user):
        """Test that profile view shows user information."""
        response = authenticated_client.get(f"/user/view/{user.id}")
        assert response.status_code == 200
        assert user.email.encode() in response.data
        assert user.first_name.encode() in response.data
        assert user.last_name.encode() in response.data

    def test_view_all_requires_authentication(self, client):
        """Test that viewing all profiles requires authentication."""
        response = client.get("/user/view/all")
        assert response.status_code in [302, 403, 404]

    def test_view_all_shows_users(self, authenticated_client, db_session, user):
        """Test that view all shows list of users."""
        response = authenticated_client.get("/user/view/all")
        assert response.status_code == 200
        assert b"All Users" in response.data
        assert user.email.encode() in response.data


class TestUserYourAccount:
    """Tests for user's own account/profile editing."""

    def test_your_account_requires_authentication(self, client):
        """Test that your account requires authentication."""
        response = client.get("/user/your_account")
        assert response.status_code in [302, 403, 404]

    def test_your_account_get_shows_form(self, authenticated_client, user):
        """Test that your account GET shows the form."""
        response = authenticated_client.get("/user/your_account")
        assert response.status_code == 200
        assert user.email.encode() in response.data

    def test_your_account_post_updates_profile(self, authenticated_client, user, db_session):
        """Test that your account POST updates user profile."""
        response = authenticated_client.post("/user/your_account", data={
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Updated",
            "last_name": "Name",
            "new_password": "",
            "confirm_password": "",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Profile updated successfully" in response.data
        
        user = db_session.query(User).get(user.id)
        assert user.first_name == "Updated"
        assert user.last_name == "Name"

    def test_your_account_post_updates_password(self, authenticated_client, user, db_session):
        """Test that your account POST can update password."""
        response = authenticated_client.post("/user/your_account", data={
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Profile and account password updated successfully" in response.data

    def test_your_account_post_password_mismatch(self, authenticated_client, user, db_session):
        """Test that your account shows error on password mismatch."""
        response = authenticated_client.post("/user/your_account", data={
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "new_password": "password123",
            "confirm_password": "password456",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Passwords must match" in response.data


class TestUserCreate:
    """Tests for creating new users."""

    def test_create_requires_admin(self, authenticated_client, user):
        """Test that creating users requires admin permission."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get("/user/create")
            assert response.status_code == 403

    def test_create_get_shows_form(self, authenticated_client, user):
        """Test that creating users shows the form (with admin permission)."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            
            response = authenticated_client.get("/user/create")
            assert response.status_code == 200
            assert b"Create User" in response.data or b"New User" in response.data or b"email" in response.data.lower()

    def test_create_post_requires_admin(self, authenticated_client, user):
        """Test that creating users POST requires admin permission."""
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

    def test_create_post_validates_email(self, authenticated_client, user):
        """Test that creating user validates email."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            
            response = authenticated_client.post("/user/create", data={
                "email": "",
                "password": "password123",
                "first_name": "New",
                "last_name": "User",
                "role": "1",
            })
            assert response.status_code == 200
            assert b"required" in response.data.lower() or b"valid" in response.data.lower()

    def test_create_post_validates_password(self, authenticated_client, user):
        """Test that creating user validates password."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            
            response = authenticated_client.post("/user/create", data={
                "email": "newuser@example.com",
                "password": "",
                "first_name": "New",
                "last_name": "User",
                "role": "1",
            })
            assert response.status_code == 200
            assert b"required" in response.data.lower() or b"valid" in response.data.lower()

    def test_create_post_creates_user(self, authenticated_client, user, db_session):
        """Test that creating user creates new user."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            
            response = authenticated_client.post("/user/create", data={
                "email": "newuser@example.com",
                "password": "password123",
                "confirm_password": "password123",
                "first_name": "New",
                "last_name": "User",
                "role": str(user.roles[0].id),
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b"User created successfully" in response.data
            
            new_user = db_session.query(User).filter_by(email="newuser@example.com").first()
            assert new_user is not None
            assert new_user.first_name == "New"
            assert new_user.last_name == "User"

    def test_create_post_validates_duplicate_email(self, authenticated_client, user, db_session):
        """Test that creating user validates duplicate email."""
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            
            response = authenticated_client.post("/user/create", data={
                "email": user.email,
                "password": "password123",
                "confirm_password": "password123",
                "first_name": "New",
                "last_name": "User",
                "role": str(user.roles[0].id),
            })
            assert response.status_code == 200
            assert b"already exists" in response.data.lower()
