""" Test configuration and fixtures for ENRG DocDB. """
import os
import shutil
import tempfile
import secrets
import string
from datetime import datetime, timedelta
import warnings
import pytest
import uuid
from flask_login.test_client import FlaskLoginClient

# Suppress deprecation and user warnings from third-party libraries
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Set DATABASE_URL before importing app to force SQLite for tests
_temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_temp_db_file.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_temp_db_file.name}"

from src.enrgdocdb.app import create_app
from src.enrgdocdb.database import Model, db
from src.enrgdocdb.models.author import Author, Institution
from src.enrgdocdb.models.document import (
    Document,
    DocumentType,
)
from src.enrgdocdb.models.event import (
    Event,
    EventSession,
)
from src.enrgdocdb.models.topic import Topic
from src.enrgdocdb.models.user import Organization, Role, RolePermission, User
from src.enrgdocdb.models.wiki import (
    WikiPage,
)


def generate_uniquifier():
    """Generate a unique identifier for the user (fs_uniquifier)."""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(64))


@pytest.fixture
def app():
    """Create application with test configuration."""
    # Reset admin views cache to avoid blueprint conflicts
    import src.enrgdocdb.admin as admin_module
    admin_module.reset_admin_views()

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()

    # Create temporary file upload folder
    temp_upload_folder = tempfile.mkdtemp()

    os.environ["TESTING"] = "true"
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{temp_db.name}",
        "SECRET_KEY": "test-secret-key-for-unit-tests-only",
        "FILE_UPLOAD_FOLDER": temp_upload_folder,
        "FILE_UPLOAD_TEMP_FOLDER": temp_upload_folder,
    })
    # Use FlaskLoginClient so login_user() properly sets current_user in tests
    app.test_client_class = FlaskLoginClient

    # Create database tables
    with app.app_context():
        Model.metadata.create_all(db.engine)

    yield app

    # Cleanup
    with app.app_context():
        Model.metadata.drop_all(db.engine)
    os.unlink(temp_db.name)
    shutil.rmtree(temp_upload_folder)


@pytest.fixture
def db_session(app):
    """Create database session for tests."""
    with app.app_context():
        yield db.session
        db.session.rollback()


@pytest.fixture
def user(db_session):
    """Create a test user."""
    # Create a unique role name to avoid conflicts across tests
    unique_suffix = str(uuid.uuid4())[:8]
    default_role = Role(
        name=f"user_{unique_suffix}",
        permissions=[
            RolePermission.VIEW,
            RolePermission.EDIT_SELF,
            RolePermission.ADD,
            RolePermission.EDIT,
        ],
    )
    db_session.add(default_role)
    db_session.commit()

    user = User(
        email=f"test_{unique_suffix}@example.com",
        username=f"testuser_{unique_suffix}",
        first_name="Test",
        last_name="User",
        password="hashed_password",
        active=True,
        fs_uniquifier=generate_uniquifier(),
    )
    user.roles.append(default_role)
    db_session.add(user)
    db_session.commit()

    # Reload user with eager loading to ensure roles are loaded
    from sqlalchemy.orm import joinedload
    user = db_session.query(User).options(
        joinedload(User.roles)
    ).filter_by(email=user.email).first()
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin user with all permissions."""
    unique_suffix = str(uuid.uuid4())[:8]
    admin_role = Role(
        name=f"admin_{unique_suffix}",
        permissions=[p.value for p in RolePermission],
    )
    admin_user = User(
        email=f"admin_{unique_suffix}@example.com",
        username=f"adminuser_{unique_suffix}",
        first_name="Admin",
        last_name="User",
        password="hashed_password",
        active=True,
        fs_uniquifier=generate_uniquifier(),
    )
    db_session.add(admin_role)
    db_session.add(admin_user)
    db_session.commit()
    return admin_user


@pytest.fixture
def organization(db_session):
    """Create a test organization."""
    org = Organization(name="Test Organization")
    db_session.add(org)
    db_session.commit()
    return org


@pytest.fixture
def role(db_session, organization):
    """Create a test role."""
    unique_suffix = str(uuid.uuid4())[:8]
    role = Role(
        name=f"user_{unique_suffix}",
        permissions=[RolePermission.VIEW, RolePermission.EDIT_SELF],
        organization_id=organization.id,
    )
    db_session.add(role)
    db_session.commit()
    return role


@pytest.fixture
def document(db_session, user, organization):
    """Create a test document."""
    doc_type = DocumentType(name="Research Paper")
    db_session.add(doc_type)
    db_session.commit()
    document = Document(
        title="Test Document",
        abstract="This is a test document",
        user_id=user.id,
        document_type_id=doc_type.id,
        organization_id=organization.id,
    )
    db_session.add(document)
    db_session.commit()
    return document


@pytest.fixture
def wiki_page(db_session, user):
    """Create a test wiki page."""
    page = WikiPage(
        title="Test Page",
        slug="test-page",
        content="Test content",
        is_pinned=False,
        organization_id=None,
    )
    db_session.add(page)
    db_session.commit()
    return page


@pytest.fixture
def topic(db_session):
    """Create a test topic."""
    topic = Topic(name="Test Topic")
    db_session.add(topic)
    db_session.commit()
    return topic


@pytest.fixture
def institution(db_session):
    """Create a test institution."""
    institution = Institution(name="Test Institution")
    db_session.add(institution)
    db_session.commit()
    return institution


@pytest.fixture
def author(db_session, institution):
    """Create a test author."""
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
def event(db_session, organization):
    """Create a test event."""
    event = Event(
        title="Test Event",
        date=datetime.now() + timedelta(days=30),
        location="Test Location",
        organization_id=organization.id,
    )
    db_session.add(event)
    db_session.commit()
    return event


@pytest.fixture
def event_session(db_session, event):
    """Create a test event session."""
    session = EventSession(
        event_id=event.id,
        session_name="Test Session",
        session_time=datetime.now() + timedelta(days=30, hours=2),
    )
    db_session.add(session)
    db_session.commit()
    return session


@pytest.fixture
def temp_upload_folder(app):
    """Get the temporary upload folder from app config."""
    return app.config["FILE_UPLOAD_FOLDER"]


@pytest.fixture
def client(app):
    """Create test client."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(app, db_session, user):
    """Create authenticated test client using FlaskLoginClient.
    
    FlaskLoginClient properly sets current_user so views that access
    current_user.id or current_user.get_organizations() don't crash.
    """
    with app.test_client(user=user) as client:
        yield client


@pytest.fixture
def client_with_auth(client, user):
    """Create authenticated test client."""
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["_remember"] = False
    yield client
