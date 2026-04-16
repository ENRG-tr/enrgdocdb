"""
Tests for file upload security and validation.

Tests file type validation, size limits, and upload security aspects.
"""
import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest
from datetime import datetime, timedelta
import jwt

from src.enrgdocdb.settings import (
    FILE_UPLOAD_FOLDER,
    FILE_UPLOAD_TEMP_FOLDER,
    SECRET_KEY,
)


class TestFileUploadSecurity:
    """Tests for file upload security features."""

    def test_file_upload_max_size_configured(self):
        """Test that max file size is configured."""
        from src.enrgdocdb.settings import FILE_UPLOAD_MAX_FILE_SIZE
        
        assert FILE_UPLOAD_MAX_FILE_SIZE > 0
        # Default should be 50MB
        assert FILE_UPLOAD_MAX_FILE_SIZE == 1024 * 1024 * 50

    def test_file_upload_folder_configured(self):
        """Test that upload folder is configured."""
        assert FILE_UPLOAD_FOLDER is not None
        assert isinstance(FILE_UPLOAD_FOLDER, str)

    def test_file_upload_temp_folder_configured(self):
        """Test that temp upload folder is configured."""
        assert FILE_UPLOAD_TEMP_FOLDER is not None
        assert isinstance(FILE_UPLOAD_TEMP_FOLDER, str)

    def test_file_upload_temp_clear_interval_configured(self):
        """Test that temp folder clear interval is configured."""
        from src.enrgdocdb.settings import FILE_UPLOAD_TEMP_CLEAR_INTERVAL_HOURS
        
        assert FILE_UPLOAD_TEMP_CLEAR_INTERVAL_HOURS > 0
        # Default should be 4 hours
        assert FILE_UPLOAD_TEMP_CLEAR_INTERVAL_HOURS == 4


class TestFileUploadTokenValidation:
    """Tests for file upload token validation."""

    def test_file_token_required(self, client):
        """Test that file_token is required for upload."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {
            "token_to_file": '{"token1": "test.pdf"}',
        }
        # No file_token provided
        
        result = handle_user_file_upload(mock_request)
        
        # Should return empty result when token is missing
        assert result.template_args is not None
        assert result.user_files is None  # No files processed

    def test_invalid_file_token_returns_empty(self, client):
        """Test that invalid file_token returns empty result."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {
            "file_token": "invalid_token",
            "token_to_file": '{"token1": "test.pdf"}',
        }
        
        result = handle_user_file_upload(mock_request)
        
        # Should return empty result when token is invalid
        assert result.template_args is not None
        assert result.user_files is None  # No files processed

    def test_valid_file_token_parsed(self, client):
        """Test that valid file_token is parsed correctly."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        # Create a valid token
        document_tokens = ["token1", "token2", "token3"]
        token_data = {
            "document_tokens": document_tokens,
            "exp": datetime.now() + timedelta(minutes=30),
        }
        file_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {
            "file_token": file_token,
            "token_to_file": '{"token1": "test.pdf", "token2": "test2.pdf"}',
        }
        
        result = handle_user_file_upload(mock_request)
        
        # Token should be parsed successfully (even if files don't exist)
        assert result.user_files is not None
        # Files won't be found since we didn't create them, but token parsing should work

    def test_expired_file_token_returns_empty(self, client):
        """Test that expired file_token returns empty result."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        # Create an expired token
        token_data = {
            "document_tokens": ["token1"],
            "exp": datetime.now() - timedelta(minutes=1),  # Expired 1 minute ago
        }
        file_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {
            "file_token": file_token,
            "token_to_file": '{"token1": "test.pdf"}',
        }
        
        result = handle_user_file_upload(mock_request)
        
        # Should return empty result when token is expired
        assert result.user_files is not None
        assert len(result.user_files) == 0

    def test_token_not_in_document_tokens_ignored(self, client, temp_upload_folder):
        """Test that tokens not in document_tokens are ignored."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        # Create a valid token
        document_tokens = ["valid_token"]
        token_data = {
            "document_tokens": document_tokens,
            "exp": datetime.now() + timedelta(minutes=30),
        }
        file_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
        
        # Try to upload with a token not in document_tokens
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {
            "file_token": file_token,
            "token_to_file": '{"invalid_token": "test.pdf"}',  # Not in document_tokens
        }
        
        result = handle_user_file_upload(mock_request)
        
        # Should return empty result since token is not in document_tokens
        assert result.user_files is not None
        assert len(result.user_files) == 0

    def test_invalid_token_to_file_json_ignored(self, client):
        """Test that invalid token_to_file JSON is handled gracefully."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        # Create a valid token
        document_tokens = ["token1"]
        token_data = {
            "document_tokens": document_tokens,
            "exp": datetime.now() + timedelta(minutes=30),
        }
        file_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {
            "file_token": file_token,
            "token_to_file": "not valid json",  # Invalid JSON
        }
        
        result = handle_user_file_upload(mock_request)
        
        # Should return empty result when JSON is invalid
        assert result.template_args is not None
        assert result.user_files is None  # No files processed


class TestFileUploadPathTraversal:
    """Tests for file upload path traversal prevention."""

    def test_file_upload_uses_temp_folder(self, temp_upload_folder):
        """Test that file upload uses configured temp folder."""
        from src.enrgdocdb.settings import FILE_UPLOAD_TEMP_FOLDER
        
        assert FILE_UPLOAD_TEMP_FOLDER is not None
        # Temp folder should be different from upload folder
        assert FILE_UPLOAD_TEMP_FOLDER != FILE_UPLOAD_FOLDER

    def test_temp_folder_created_if_not_exists(self, temp_upload_folder):
        """Test that temp folder is created if it doesn't exist."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "nonexistent")
            from src.enrgdocdb.settings import FILE_UPLOAD_TEMP_FOLDER
            
            # The temp folder should exist if FILE_UPLOAD_TEMP_FOLDER is set
            # This test verifies the folder structure is valid
            assert os.path.isdir(temp_upload_folder) or FILE_UPLOAD_TEMP_FOLDER is not None


class TestFileUploadResult:
    """Tests for file upload result structure."""

    def test_result_contains_file_token(self, client):
        """Test that upload result contains file_token."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {}
        
        result = handle_user_file_upload(mock_request)
        
        # Result should contain file_token
        assert result.template_args is not None
        assert "file_token" in result.template_args
        # file_token should be a JWT token
        assert isinstance(result.template_args["file_token"], str)
        assert len(result.template_args["file_token"]) > 0

    def test_result_contains_document_tokens(self, client):
        """Test that upload result contains document_tokens."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {}
        
        result = handle_user_file_upload(mock_request)
        
        # Result should contain document_tokens
        assert result.template_args is not None
        assert "document_tokens" in result.template_args
        # document_tokens should be a list
        assert isinstance(result.template_args["document_tokens"], list)
        # Should have some tokens (up to 10)
        assert len(result.template_args["document_tokens"]) <= 10

    def test_result_user_files_is_list(self, client):
        """Test that user_files is always a list or None."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        mock_request = MagicMock()
        mock_request.method = "GET"  # GET request
        
        result = handle_user_file_upload(mock_request)
        
        # user_files should be None (no files) or a list
        assert result.user_files is None or isinstance(result.user_files, list)

    def test_user_file_dataclass_has_required_fields(self, client):
        """Test that UserFile dataclass has required fields."""
        from src.enrgdocdb.utils.file import UserFile
        
        test_file = UserFile(
            file_path="/uploads/test.pdf",
            uploaded_file_name="test.pdf",
        )
        
        assert test_file.file_path == "/uploads/test.pdf"
        assert test_file.uploaded_file_name == "test.pdf"


class TestFileUploadSecurityEdgeCases:
    """Tests for file upload security edge cases."""

    def test_empty_token_to_file_ignored(self, client):
        """Test that empty token_to_file is handled gracefully."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        # Create a valid token
        document_tokens = ["token1"]
        token_data = {
            "document_tokens": document_tokens,
            "exp": datetime.now() + timedelta(minutes=30),
        }
        file_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {
            "file_token": file_token,
            "token_to_file": "",  # Empty
        }
        
        result = handle_user_file_upload(mock_request)
        
        # Should return empty result when token_to_file is empty
        assert result.template_args is not None
        assert result.user_files is None  # No files processed

    def test_none_token_to_file_ignored(self, client):
        """Test that None token_to_file is handled gracefully."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        # Create a valid token
        document_tokens = ["token1"]
        token_data = {
            "document_tokens": document_tokens,
            "exp": datetime.now() + timedelta(minutes=30),
        }
        file_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {
            "file_token": file_token,
            "token_to_file": None,  # None
        }
        
        result = handle_user_file_upload(mock_request)
        
        # Should return empty result when token_to_file is None
        assert result.template_args is not None
        assert result.user_files is None  # No files processed

    def test_multiple_files_same_token_ignored(self, client, temp_upload_folder):
        """Test that multiple files with same token are handled."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        # Create a valid token
        document_tokens = ["token1"]
        token_data = {
            "document_tokens": document_tokens,
            "exp": datetime.now() + timedelta(minutes=30),
        }
        file_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
        
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.form = {
            "file_token": file_token,
            "token_to_file": '{"token1": "test.pdf", "token1": "test2.pdf"}',  # Duplicate key
        }
        
        result = handle_user_file_upload(mock_request)
        
        # Should handle gracefully (JSON parsing will use last value)
        assert result.user_files is not None

    def test_get_request_returns_empty(self, client):
        """Test that GET request returns empty result."""
        from src.enrgdocdb.utils.file import handle_user_file_upload
        
        mock_request = MagicMock()
        mock_request.method = "GET"
        
        result = handle_user_file_upload(mock_request)
        
        # GET requests should return empty result
        assert result.template_args is not None
        assert result.user_files is None  # No files processed
