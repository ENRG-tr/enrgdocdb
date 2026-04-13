"""
View tests for Document file upload and download operations.

Tests file upload endpoints, download endpoints, and file management with
proper permission enforcement.
"""
import os
from unittest.mock import patch, MagicMock


class TestDocumentFileUpload:
    """Tests for document file upload views."""

    
    def test_upload_files_requires_authentication(self, client):
        """Test that file upload requires authentication."""
        response = client.get("/documents/upload_files?id=1")
        assert response.status_code == 302

    
    def test_upload_files_requires_document(self, authenticated_client, db_session):
        """Test that file upload requires a valid document ID."""
        response = authenticated_client.get("/documents/upload_files")
        assert response.status_code == 404

    
    def test_upload_files_requires_permission(self, authenticated_client, db_session, user, organization):
        """Test that file upload requires EDIT permission."""
        from src.enrgdocdb.models.document import Document, DocumentType
        
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        db_session.commit()

        document = Document(
            title="Test Document",
            abstract="Test abstract",
            user_id=user.id,
            document_type_id=doc_type.id,
            organization_id=organization.id,
        )
        db_session.add(document)
        db_session.commit()

        # Mock permission check to return False
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/documents/upload_files?id={document.id}")
            assert response.status_code == 403

    
    def test_upload_files_get_shows_form(self, authenticated_client, db_session, user, organization):
        """Test that file upload GET shows the form."""
        from src.enrgdocdb.models.document import Document, DocumentType
        
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        db_session.commit()

        document = Document(
            title="Test Document",
            abstract="Test abstract",
            user_id=user.id,
            document_type_id=doc_type.id,
            organization_id=organization.id,
        )
        db_session.add(document)
        db_session.commit()

        response = authenticated_client.get(f"/documents/upload_files?id={document.id}")
        assert response.status_code == 200
        assert b"Upload Files" in response.data
        assert b"Test Document" in response.data

    
    def test_upload_files_post_uploads_files(self, authenticated_client, db_session, user, organization, temp_upload_folder):
        """Test that file upload POST uploads files to document."""
        from src.enrgdocdb.models.document import Document, DocumentType, DocumentFile
        
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        db_session.commit()

        document = Document(
            title="Test Document",
            abstract="Test abstract",
            user_id=user.id,
            document_type_id=doc_type.id,
            organization_id=organization.id,
        )
        db_session.add(document)
        db_session.commit()

        # Create a test file
        test_file_path = os.path.join(temp_upload_folder, "test.pdf")
        with open(test_file_path, "w") as f:
            f.write("test content")

        # Simulate file upload
        with patch("src.enrgdocdb.views.document.handle_user_file_upload") as mock_upload:
            mock_result = MagicMock()
            mock_result.user_files = [MagicMock()]
            mock_result.user_files[0].uploaded_file_name = "test.pdf"
            mock_result.user_files[0].file_path = test_file_path
            mock_upload.return_value = mock_result

            response = authenticated_client.post(f"/documents/upload_files?id={document.id}", data={
                "files": "test.pdf",
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b"Files were uploaded successfully" in response.data
            
            # Verify file was added to document
            files = db_session.query(DocumentFile).filter_by(document_id=document.id).all()
            assert len(files) > 0

    
    def test_upload_files_404_for_nonexistent_document(self, authenticated_client):
        """Test that uploading to nonexistent document returns 404."""
        response = authenticated_client.get("/documents/upload_files?id=99999")
        assert response.status_code == 404


class TestDocumentFileDownload:
    """Tests for document file download views."""

    
    def test_download_file_requires_authentication(self, client):
        """Test that file download requires authentication."""
        response = client.get("/documents/download-file/1")
        assert response.status_code == 302

    
    def test_download_file_requires_permission(self, authenticated_client, db_session, user, organization):
        """Test that file download requires VIEW permission."""
        from src.enrgdocdb.models.document import Document, DocumentType, DocumentFile
        
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        db_session.commit()

        document = Document(
            title="Test Document",
            abstract="Test abstract",
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

        # Mock permission check to return False
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/documents/download-file/{file.id}")
            assert response.status_code == 403

    
    def test_download_file_404_for_nonexistent(self, authenticated_client):
        """Test that downloading nonexistent file returns 404."""
        response = authenticated_client.get("/documents/download-file/99999")
        assert response.status_code == 404

    
    def test_download_file_sends_file(self, authenticated_client, db_session, user, organization, temp_upload_folder):
        """Test that file download sends the actual file."""
        from src.enrgdocdb.models.document import Document, DocumentType, DocumentFile
        
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        db_session.commit()

        document = Document(
            title="Test Document",
            abstract="Test abstract",
            user_id=user.id,
            document_type_id=doc_type.id,
            organization_id=organization.id,
        )
        db_session.add(document)
        db_session.commit()

        # Create a real test file
        test_content = b"Test file content for download"
        test_file_path = os.path.join(temp_upload_folder, "test.pdf")
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        file = DocumentFile(
            document_id=document.id,
            file_name="test.pdf",
            real_file_name="test.pdf",
        )
        db_session.add(file)
        db_session.commit()

        # Mock permission check to return True
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = True
            
            # Mock send_from_directory to return the file content
            with patch("src.enrgdocdb.views.document.send_from_directory") as mock_send:
                mock_send.return_value = test_content
                
                response = authenticated_client.get(f"/documents/download-file/{file.id}")
                assert response.status_code == 200
                mock_send.assert_called_once()


class TestDocumentFileManagement:
    """Tests for document file management operations."""

    
    def test_delete_file_requires_authentication(self, client):
        """Test that file deletion requires authentication."""
        response = client.get("/documents/delete-file/1")
        assert response.status_code == 302

    
    def test_delete_file_requires_permission(self, authenticated_client, db_session, user, organization):
        """Test that file deletion requires EDIT permission."""
        from src.enrgdocdb.models.document import Document, DocumentType, DocumentFile
        
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        db_session.commit()

        document = Document(
            title="Test Document",
            abstract="Test abstract",
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

        # Mock permission check to return False
        with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
            mock_perm.return_value = False
            
            response = authenticated_client.get(f"/documents/delete-file/{file.id}")
            assert response.status_code == 403

    
    def test_delete_file_removes_file(self, authenticated_client, db_session, user, organization):
        """Test that file deletion removes file from database."""
        from src.enrgdocdb.models.document import Document, DocumentType, DocumentFile
        
        doc_type = DocumentType(name="Research Paper")
        db_session.add(doc_type)
        db_session.commit()

        document = Document(
            title="Test Document",
            abstract="Test abstract",
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

        response = authenticated_client.get(f"/documents/delete-file/{file.id}", follow_redirects=True)
        assert response.status_code == 200
        assert b"File was deleted successfully" in response.data
        
        # Verify file was deleted
        deleted = db_session.query(DocumentFile).get(file.id)
        assert deleted is None

    
    def test_delete_file_404_for_nonexistent(self, authenticated_client):
        """Test that deleting nonexistent file returns 404."""
        response = authenticated_client.get("/documents/delete-file/99999")
        assert response.status_code == 404
