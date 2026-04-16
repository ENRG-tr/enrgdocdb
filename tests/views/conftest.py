"""
View test configuration and fixtures for ENRG DocDB.

Provides authenticated test clients, mock user context, and common view test helpers.
"""
import os
import tempfile
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch


from src.enrgdocdb.models.user import User
from src.enrgdocdb.models.document import Document, DocumentType
from src.enrgdocdb.models.wiki import WikiPage
from src.enrgdocdb.models.event import Event
from src.enrgdocdb.models.author import Author, Institution
from src.enrgdocdb.models.topic import Topic


def generate_uniquifier():
    """Generate a unique identifier for the user (fs_uniquifier)."""
    import string
    import secrets
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(64))


@pytest.fixture
def admin_authenticated_client(app, db_session, admin_user):
    """Create an authenticated admin test client for view tests.
    
    Uses FlaskLoginClient so current_user is properly set to `admin_user`.
    """
    with app.test_client(user=admin_user) as client:
        yield client


@pytest.fixture
def mock_current_user(user):
    """Mock Flask-Login's current_user for view tests."""
    with patch("src.enrgdocdb.views.document.current_user") as mock_user:
        mock_user.id = user.id
        mock_user.is_authenticated = True
        mock_user.is_admin = False
        mock_user.role = user.role
        yield mock_user


@pytest.fixture
def mock_admin_current_user(admin_user):
    """Mock Flask-Login's current_user as admin for view tests."""
    with patch("src.enrgdocdb.views.document.current_user") as mock_user:
        mock_user.id = admin_user.id
        mock_user.is_authenticated = True
        mock_user.is_admin = True
        mock_user.role = admin_user.role
        yield mock_user


@pytest.fixture
def mock_unauthenticated_user():
    """Mock Flask-Login's current_user as unauthenticated for view tests."""
    with patch("src.enrgdocdb.views.document.current_user") as mock_user:
        mock_user.is_authenticated = False
        yield mock_user


@pytest.fixture
def mock_permission_check(user):
    """Mock permission_check function for view tests."""
    with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
        mock_perm.return_value = True
        yield mock_perm


@pytest.fixture
def mock_permission_check_false():
    """Mock permission_check to return False for view tests."""
    with patch("src.enrgdocdb.utils.security.permission_check") as mock_perm:
        mock_perm.return_value = False
        yield mock_perm


@pytest.fixture
def test_document(db_session, user, organization):
    """Create a test document for view tests."""
    doc_type = DocumentType(name="Research Paper")
    db_session.add(doc_type)
    db_session.commit()
    
    document = Document(
        title="Test Document for Views",
        abstract="This is a test document for view testing",
        user_id=user.id,
        document_type_id=doc_type.id,
        organization_id=organization.id,
    )
    db_session.add(document)
    db_session.commit()
    return document


@pytest.fixture
def test_wiki_page(db_session, user):
    """Create a test wiki page for view tests."""
    page = WikiPage(
        title="Test Wiki Page",
        slug="test-wiki-page",
        content="Test wiki page content",
        is_pinned=False,
        organization_id=None,
    )
    db_session.add(page)
    db_session.commit()
    return page


@pytest.fixture
def test_event(db_session, organization):
    """Create a test event for view tests."""
    event = Event(
        title="Test Event for Views",
        date=datetime.now() + timedelta(days=30),
        location="Test Location",
        organization_id=organization.id,
    )
    db_session.add(event)
    db_session.commit()
    return event


@pytest.fixture
def test_institution(db_session):
    """Create a test institution for view tests."""
    institution = Institution(name="Test Institution")
    db_session.add(institution)
    db_session.commit()
    return institution


@pytest.fixture
def test_author(db_session, institution):
    """Create a test author for view tests."""
    author = Author(
        first_name="Test",
        last_name="Author",
        email="author@example.com",
        institution_id=institution.id,
    )
    db_session.add(author)
    db_session.commit()
    return author


@pytest.fixture
def test_topic(db_session):
    """Create a test topic for view tests."""
    topic = Topic(name="Test Topic")
    db_session.add(topic)
    db_session.commit()
    return topic


@pytest.fixture
def temp_upload_folder():
    """Create a temporary upload folder for file upload tests."""
    folder = tempfile.mkdtemp()
    yield folder
    import shutil
    shutil.rmtree(folder, ignore_errors=True)


@pytest.fixture
def sample_pdf_file(temp_upload_folder):
    """Create a sample PDF file for upload tests."""
    
    # Create a minimal valid PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj xref 0 4 0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000102 00000 n \ntrailer<</Size 4/Root 1 0 R>>startxref 179%%EOF"
    
    pdf_path = os.path.join(temp_upload_folder, "test_document.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_content)
    
    yield pdf_path, len(pdf_content)
    
    os.unlink(pdf_path)
