import os
from datetime import datetime

from flask import abort, flash, redirect, request, url_for
from flask import current_app as app
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.theme import Bootstrap4Theme
from flask_login import current_user
from flask_security.utils import hash_password
from wtforms import HiddenField, PasswordField, TextAreaField

from .database import db
from .models.author import Author, Institution
from .models.document import Document, DocumentFile, DocumentType
from .models.event import Event, EventSession, TalkNote
from .models.topic import Topic
from .models.user import (
    ROLES_PERMISSIONS_BY_ORGANIZATION,
    Organization,
    Role,
    RolePermission,
    User,
)
from .models.wiki import WikiPage, WikiPagePermission
from .utils.admin import EditInlineModelField, RichTextField
from .utils.logging import AuditLogger, get_logger
from .utils.security import permission_check

admin = Admin(
    name="ENRG DocDB Admin",
    theme=Bootstrap4Theme(base_template="docdb/admin/base.html"),
    index_view=None,
)


class AdminView(ModelView):
    # disable edit for created_at, updated_at, deleted_at
    form_excluded_columns = ["created_at", "updated_at", "deleted_at"]

    # Audit logger instance
    _audit_logger = None

    @property
    def audit_logger(self):
        """Get or create the audit logger instance."""
        if self._audit_logger is None:
            self._audit_logger = AuditLogger(get_logger(__name__))
        return self._audit_logger

    def is_accessible(self):
        return_url = request.args.get("url") or url_for("index.index")
        if request.path.endswith("/edit/"):
            id = request.args.get("id")
            if id is None:
                return redirect(return_url)
            model = self.get_one(id)
            return permission_check(model, RolePermission.EDIT)
        elif request.path.endswith("/new/"):
            return permission_check(self.model, RolePermission.ADD)
        return permission_check(None, RolePermission.ADMIN)

    def inaccessible_callback(self, name, **kwargs):
        return abort(403)

    @expose("/")
    def index_view(self):
        return redirect(url_for("index.index"))

    def _modify_form_query(self, form, obj, is_create):
        return form

    def create_form(self, obj=None):
        form = super().edit_form(obj)
        return self._modify_form_query(form, obj, True)

    def edit_form(self, obj=None):
        form = super().edit_form(obj)
        return self._modify_form_query(form, obj, False)

    def _on_change(self, form, model, is_created):
        return True

    def on_model_change(self, form, model, is_created):
        """Called after the model is created or updated."""
        result = super().on_model_change(form, model, is_created)

        # Log the change to the audit trail
        if current_user.is_authenticated:
            user_email = current_user.email
            resource_type = model.__class__.__name__
            resource_id = model.id if hasattr(model, "id") else None

            if is_created:
                self.audit_logger.create(resource_type, resource_id, user_email)
            else:
                self.audit_logger.update(resource_type, resource_id, user_email)

        return result

    def on_model_delete(self, form, model):
        """Called after the model is deleted."""
        # Log the deletion to the audit trail
        if current_user.is_authenticated:
            user_email = current_user.email
            resource_type = model.__class__.__name__
            resource_id = model.id if hasattr(model, "id") else None

            self.audit_logger.delete(resource_type, resource_id, user_email)

        return super().on_model_delete(form, model)

    def update_model(self, form, model):
        if not self._on_change(form, model, False):
            return False
        return super().update_model(form, model)

    def create_model(self, form):
        if not self._on_change(form, None, True):
            return False
        return super().create_model(form)


class WikiPageAdminView(AdminView):
    form_columns = [
        "title",
    ]
    inline_models = [
        (WikiPagePermission, {"form_columns": ["id", "role", "permission"]}),
    ]
    form_overrides = {
        "content": RichTextField,
    }
    form_widget_args = {"title": {"readonly": True}}

    def is_accessible(self):
        if request.path.endswith("/edit/"):
            id = request.args.get("id")
            if id:
                model = self.get_one(id)
                return permission_check(model, RolePermission.ADMIN)
        return permission_check(None, RolePermission.ADMIN)


class DocumentAdminView(AdminView):
    form_columns = [
        "id",
        "title",
        "abstract",
        "topics",
        "document_type",
        "authors",
        "files",
        "upload_files",
    ]
    # make abstract a textarea
    form_extra_fields = {
        "id": HiddenField(),
        "abstract": TextAreaField("Abstract"),
        "upload_files": EditInlineModelField(
            "document.upload_files", fas_custom_class="fa-upload"
        ),
    }
    can_create = False

    def _modify_form_query(self, form, obj, is_create):
        form.files.query = db.session.query(DocumentFile).filter(
            DocumentFile.document_id == obj.id
        )
        return form


class TopicAdminView(AdminView):
    form_columns = ["name", "parent_topic"]

    def _modify_form_query(self, form, obj, is_create):
        form.parent_topic.query = db.session.query(Topic).filter(
            Topic.parent_topic_id.is_(None)
        )
        if not is_create:
            form.parent_topic.query = form.parent_topic.query.filter(Topic.id != obj.id)

        return form


class AuthorAdminView(AdminView):
    form_columns = ["first_name", "last_name", "email", "phone", "institution"]


class InstitutionAdminView(AdminView):
    form_columns = ["name"]


class DocumentTypeAdminView(AdminView):
    form_columns = ["name"]


class OrganizationAdminView(AdminView):
    form_columns = ["name"]

    # after committing the form, create new roles based on organization
    def after_model_change(self, form, model, is_created):
        if not is_created:
            return
        for (
            sample_role,
            sample_role_permissions,
        ) in ROLES_PERMISSIONS_BY_ORGANIZATION.items():
            role = Role(name=sample_role, organization_id=model.id)
            role.permissions = [x.value for x in sample_role_permissions]
            db.session.add(role)
        db.session.commit()


class UserAdminView(AdminView):
    form_columns = [
        "first_name",
        "last_name",
        "email",
        "roles",
        "password",
        "password_again",
    ]

    form_extra_fields = {
        "password": PasswordField("Password"),
        "password_again": PasswordField("Password Again"),
    }

    def _on_change(self, form, model, is_created):
        if form.password.data is None or form.password.data == "":
            return True
        if form.password.data != form.password_again.data:
            flash("Passwords do not match", "error")
            return False
        if len(form.password.data) < 8:
            flash("Password must be at least 8 characters", "error")
            return False

        model.password = hash_password(form.password.data)
        return True

    def delete_model(self, model: User):
        model = db.session.query(User).filter(User.id == model.id).one()
        model.deleted_at = datetime.now()
        db.session.commit()
        return True


class EventAdminView(AdminView):
    form_columns = [
        "title",
        "date",
        "organization",
        "location",
        "event_url",
        "topics",
        "moderators",
    ]

    column_labels = {
        "event_sessions": "Session",
    }

    inline_models = [
        (
            EventSession,
            {
                "form_columns": [
                    "id",
                    "edit_session",
                    "session_name",
                    "session_time",
                    "external_url",
                    "topics",
                    "moderators",
                ],
                "form_extra_fields": {
                    # Show a link anchor to edit the session
                    "edit_session": EditInlineModelField(
                        edit_view="admin_EventSession.edit_view",
                        label="Edit Session",
                    ),
                },
            },
        )
    ]

    def _modify_form_query(self, form, obj, is_create):
        form.organization.query = db.session.query(Organization).filter(
            Organization.id.in_([x.id for x in current_user.get_organizations()])
        )
        form.moderators.query = db.session.query(User).filter(User.deleted_at == None)  # noqa: E711
        return form


class EventSessionAdminView(AdminView):
    form_columns = [
        "session_name",
        "session_time",
        "external_url",
        "topics",
        "moderators",
    ]

    inline_models = [
        (
            TalkNote,
            {
                "form_columns": [
                    "id",
                    "start_time",
                    "talk_title",
                    "document",
                ],
                "form_extra_fields": {
                    # Show a link anchor to edit the session
                    "edit_session": EditInlineModelField(
                        edit_view="admin_TalkNote.edit_view"
                    ),
                },
            },
        )
    ]


def get_admin_view_endpoint(model):
    return f"admin_{model.__name__}"


class SessionProxy:
    def __getattr__(self, name):
        with app.test_request_context():
            session = db.session
            return getattr(session, name)


# Cache for admin views to avoid re-creation
_admin_views_cache = None
_session_proxy = None


def get_admin_views():
    """Get admin views

    Views are cached to avoid Flask blueprint name conflicts when the app
    is recreated (e.g., in tests).

    Returns an empty list when running in test mode to avoid blueprint conflicts.
    """
    global _admin_views_cache, _session_proxy

    # Return empty list in test mode to avoid blueprint conflicts
    if os.environ.get("TESTING", "").lower() == "true":
        return []

    global _admin_views_cache, _session_proxy

    # Create session proxy lazily to avoid import-time app context issues
    if _session_proxy is None:
        _session_proxy = SessionProxy()

    if _admin_views_cache is not None:
        return _admin_views_cache

    _admin_views_cache = [
        DocumentAdminView(
            Document, _session_proxy, endpoint=get_admin_view_endpoint(Document)
        ),
        TopicAdminView(Topic, _session_proxy, endpoint=get_admin_view_endpoint(Topic)),
        AuthorAdminView(
            Author, _session_proxy, endpoint=get_admin_view_endpoint(Author)
        ),
        InstitutionAdminView(
            Institution, _session_proxy, endpoint=get_admin_view_endpoint(Institution)
        ),
        DocumentTypeAdminView(
            DocumentType, _session_proxy, endpoint=get_admin_view_endpoint(DocumentType)
        ),
        OrganizationAdminView(
            Organization, _session_proxy, endpoint=get_admin_view_endpoint(Organization)
        ),
        UserAdminView(User, _session_proxy, endpoint=get_admin_view_endpoint(User)),
        EventAdminView(Event, _session_proxy, endpoint=get_admin_view_endpoint(Event)),
        EventSessionAdminView(
            EventSession, _session_proxy, endpoint=get_admin_view_endpoint(EventSession)
        ),
        WikiPageAdminView(
            WikiPage, _session_proxy, endpoint=get_admin_view_endpoint(WikiPage)
        ),
    ]
    return _admin_views_cache


def reset_admin_views():
    """Reset the admin views cache (useful for testing)."""
    global _admin_views_cache, _session_proxy
    _admin_views_cache = None
    _session_proxy = None


views = property(get_admin_views)
