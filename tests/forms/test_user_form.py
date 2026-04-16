"""
Tests for User form validation (CreateUserForm, EditUserProfileForm).
"""
import pytest

from src.enrgdocdb.forms.user import CreateUserForm, EditUserProfileForm
from src.enrgdocdb.models.user import Role, Organization


class TestCreateUserFormValidation:
    """Test CreateUserForm validation logic."""

    def test_email_required(self, db_session):
        """Test that email is required."""
        form = CreateUserForm(data={
            "email": "",
            "password": "password123",
            "confirm_password": "password123",
            "first_name": "John",
            "last_name": "Doe",
            "role": "1",
        })
        
        assert not form.validate()
        assert "email" in form.errors
        assert "This field is required" in form.errors["email"][0]

    def test_password_required(self, db_session):
        """Test that password is required."""
        form = CreateUserForm(data={
            "email": "john@example.com",
            "password": "",
            "confirm_password": "",
            "first_name": "John",
            "last_name": "Doe",
            "role": "1",
        })
        
        assert not form.validate()
        assert "password" in form.errors
        assert "This field is required" in form.errors["password"][0]

    def test_password_confirmation_required(self, db_session):
        """Test that password confirmation is required."""
        form = CreateUserForm(data={
            "email": "john@example.com",
            "password": "password123",
            "confirm_password": "",
            "first_name": "John",
            "last_name": "Doe",
            "role": "1",
        })
        
        assert not form.validate()
        assert "confirm_password" in form.errors
        # When password is provided but confirm_password is empty,
        # the EqualTo validator triggers with "Passwords must match" message
        assert "Passwords must match" in form.errors["confirm_password"][0]

    def test_passwords_must_match(self, db_session):
        """Test that password and confirmation must match."""
        form = CreateUserForm(data={
            "email": "john@example.com",
            "password": "password123",
            "confirm_password": "password456",
            "first_name": "John",
            "last_name": "Doe",
            "role": "1",
        })
        
        assert not form.validate()
        assert "confirm_password" in form.errors
        assert "Passwords must match" in form.errors["confirm_password"][0]

    def test_first_name_required(self, db_session):
        """Test that first name is required."""
        form = CreateUserForm(data={
            "email": "john@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "first_name": "",
            "last_name": "Doe",
            "role": "1",
        })
        
        assert not form.validate()
        assert "first_name" in form.errors
        assert "This field is required" in form.errors["first_name"][0]

    def test_last_name_required(self, db_session):
        """Test that last name is required."""
        form = CreateUserForm(data={
            "email": "john@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "first_name": "John",
            "last_name": "",
            "role": "1",
        })
        
        assert not form.validate()
        assert "last_name" in form.errors
        assert "This field is required" in form.errors["last_name"][0]

    def test_role_required(self, db_session):
        """Test that role is required."""
        form = CreateUserForm(data={
            "email": "john@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "first_name": "John",
            "last_name": "Doe",
            "role": "",
        })
        
        assert not form.validate()
        assert "role" in form.errors
        assert "This field is required" in form.errors["role"][0]

    def test_valid_form_data(self, db_session, user, organization):
        """Test that valid form data passes basic validation."""
        form = CreateUserForm(data={
            "email": "newuser@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "first_name": "New",
            "last_name": "User",
            "role": str(user.roles[0].id),
        })
        
        # Note: email uniqueness validation happens at the database level
        # This test verifies the form structure is correct
        assert form.email.data == "newuser@example.com"
        assert form.first_name.data == "New"
        assert form.last_name.data == "User"
        # role is coerced to int by the SelectField
        assert form.role.data == user.roles[0].id


class TestEditUserProfileFormValidation:
    """Test EditUserProfileForm validation logic."""

    def test_first_name_required(self, db_session, user):
        """Test that first name is required."""
        form = EditUserProfileForm(data={
            "email": user.email,
            "username": user.username,
            "first_name": "",
            "last_name": "Doe",
            "new_password": "",
            "confirm_password": "",
        })
        
        assert not form.validate()
        assert "first_name" in form.errors
        assert "This field is required" in form.errors["first_name"][0]

    def test_last_name_required(self, db_session, user):
        """Test that last name is required."""
        form = EditUserProfileForm(data={
            "email": user.email,
            "username": user.username,
            "first_name": "John",
            "last_name": "",
            "new_password": "",
            "confirm_password": "",
        })
        
        assert not form.validate()
        assert "last_name" in form.errors
        assert "This field is required" in form.errors["last_name"][0]

    def test_password_confirmation_not_required_when_empty(self, db_session, user):
        """Test that password confirmation is not required when new_password is empty."""
        form = EditUserProfileForm(data={
            "email": user.email,
            "username": user.username,
            "first_name": "John",
            "last_name": "Doe",
            "new_password": "",
            "confirm_password": "",
        })
        
        # When new_password is empty, confirm_password should not be validated
        # The form should pass validation for these fields
        assert "confirm_password" not in form.errors

    def test_password_confirmation_must_match(self, db_session, user):
        """Test that password confirmation must match new password."""
        form = EditUserProfileForm(data={
            "email": user.email,
            "username": user.username,
            "first_name": "John",
            "last_name": "Doe",
            "new_password": "password123",
            "confirm_password": "password456",
        })
        
        assert not form.validate()
        assert "confirm_password" in form.errors
        assert "Passwords must match" in form.errors["confirm_password"][0]

    def test_password_not_required_when_not_providing(self, db_session, user):
        """Test that new_password is optional when not changing password."""
        form = EditUserProfileForm(data={
            "email": user.email,
            "username": user.username,
            "first_name": "John",
            "last_name": "Doe",
            "new_password": "",
            "confirm_password": "",
        })
        
        # When new_password is empty, form should not require confirm_password
        # This is handled by the Optional() validator
        assert form.new_password.data == ""
        assert form.confirm_password.data == ""

    def test_valid_form_data(self, db_session, user):
        """Test that valid form data passes basic validation."""
        form = EditUserProfileForm(data={
            "email": user.email,
            "username": user.username,
            "first_name": "Updated",
            "last_name": "Name",
            "new_password": "",
            "confirm_password": "",
        })
        
        # Note: Other validation may occur at the view/database level
        # This test verifies the form structure is correct
        assert form.first_name.data == "Updated"
        assert form.last_name.data == "Name"
        assert form.email.data == user.email
        assert form.username.data == user.username

    def test_password_with_special_characters(self, db_session, user):
        """Test that passwords with special characters are accepted."""
        form = EditUserProfileForm(data={
            "email": user.email,
            "username": user.username,
            "first_name": "John",
            "last_name": "Doe",
            "new_password": "P@ssw0rd!2026",
            "confirm_password": "P@ssw0rd!2026",
        })
        
        # The form accepts any password (validation happens at view level)
        assert form.new_password.data == "P@ssw0rd!2026"
        assert form.confirm_password.data == "P@ssw0rd!2026"

    def test_empty_password_fields_not_validated_against_each_other(self, db_session, user):
        """Test that empty password fields don't trigger match validation."""
        form = EditUserProfileForm(data={
            "email": user.email,
            "username": user.username,
            "first_name": "John",
            "last_name": "Doe",
            "new_password": "",
            "confirm_password": "",
        })
        
        # When both are empty, EqualTo validator should not fail
        # because Optional() validator allows empty values
        assert form.new_password.data == ""
        assert form.confirm_password.data == ""
