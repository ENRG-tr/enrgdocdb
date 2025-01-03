import os
from datetime import datetime

from flask import current_app as app
from flask import redirect, request, url_for
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.theme import Bootstrap4Theme
from wtforms import TextAreaField

from database import db
from models.author import Author, Institution
from models.document import Document, DocumentType
from models.topic import Topic
from models.user import (
    ROLES_PERMISSIONS_BY_ORGANIZATION,
    Organization,
    Role,
    RolePermission,
    User,
)
from settings import FILE_UPLOAD_FOLDER
from utils.security import permission_check

admin = Admin(
    name="ENRG DocDB Admin",
    theme=Bootstrap4Theme(base_template="docdb/admin/base.html"),
    index_view=None,
)


class AdminView(ModelView):
    # disable edit for created_at, updated_at, deleted_at
    form_excluded_columns = ["created_at", "updated_at", "deleted_at"]

    def is_accessible(self):
        return_url = request.args.get("url") or url_for("index.index")
        if request.path.endswith("/edit/"):
            id = request.args.get("id")
            if id is None:
                return redirect(return_url)
            model = self.get_one(id)
            return permission_check(model, RolePermission.EDIT)
        return permission_check(None, RolePermission.ADMIN)

    @expose("/")
    def index_view(self):
        return redirect(url_for("index.index"))


class DocumentAdminView(AdminView):
    form_columns = ["title", "abstract", "topics", "document_type", "authors"]
    # make abstract a textarea
    form_extra_fields = {
        "abstract": TextAreaField("Abstract"),
    }
    can_create = False

    def on_model_delete(self, model: Document):
        # Delete files of documents from disk
        for file in model.files:
            os.remove(os.path.join(FILE_UPLOAD_FOLDER, file.real_file_name))


class TopicAdminView(AdminView):
    form_columns = ["name"]


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
            role.permissions = []
            role.permissions.extend([x.value for x in sample_role_permissions])
            db.session.add(role)
        db.session.commit()


class UserAdminView(AdminView):
    form_columns = ["first_name", "last_name", "email", "roles"]

    def delete_model(self, model: User):
        model = db.session.query(User).filter(User.id == model.id).one()
        model.deleted_at = datetime.now()
        db.session.commit()
        return True


def get_admin_view_endpoint(model):
    return f"admin_{model.__name__}"


class SessionProxy:
    def __getattr__(self, name):
        with app.test_request_context():
            session = db.session
            return getattr(session, name)


session_proxy = SessionProxy()

views = [
    DocumentAdminView(
        Document, session_proxy, endpoint=get_admin_view_endpoint(Document)
    ),
    TopicAdminView(Topic, session_proxy, endpoint=get_admin_view_endpoint(Topic)),
    AuthorAdminView(Author, session_proxy, endpoint=get_admin_view_endpoint(Author)),
    InstitutionAdminView(
        Institution, session_proxy, endpoint=get_admin_view_endpoint(Institution)
    ),
    DocumentTypeAdminView(
        DocumentType, session_proxy, endpoint=get_admin_view_endpoint(DocumentType)
    ),
    OrganizationAdminView(
        Organization, session_proxy, endpoint=get_admin_view_endpoint(Organization)
    ),
    UserAdminView(User, session_proxy, endpoint=get_admin_view_endpoint(User)),
]
