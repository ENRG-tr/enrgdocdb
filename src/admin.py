from datetime import datetime

from flask import redirect, url_for
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.theme import Bootstrap4Theme
from wtforms import TextAreaField

from database import db
from models.author import Author, Institution
from models.document import Document, DocumentType
from models.topic import Topic
from models.user import ROLES_PERMISSIONS, Organization, Role, User

admin = Admin(
    name="ENRG DocDB Admin",
    theme=Bootstrap4Theme(base_template="docdb/admin/base.html"),
    index_view=None,
)


class AdminView(ModelView):
    # disable edit for created_at, updated_at, deleted_at
    form_excluded_columns = ["created_at", "updated_at", "deleted_at"]

    def is_accessible(self):
        return True  # current_user.has_role("admin")

    @expose("/")
    def index_view(self):
        return redirect(url_for("index.index"))


class DocumentAdminView(AdminView):
    form_columns = ["title", "abstract", "topics", "files"]
    # make abstract a textarea
    form_extra_fields = {
        "abstract": TextAreaField("Abstract"),
    }
    can_create = False


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
        for sample_role, sample_role_permissions in ROLES_PERMISSIONS.items():
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


views = [
    DocumentAdminView(Document, db.session, endpoint=get_admin_view_endpoint(Document)),
    TopicAdminView(Topic, db.session, endpoint=get_admin_view_endpoint(Topic)),
    AuthorAdminView(Author, db.session, endpoint=get_admin_view_endpoint(Author)),
    InstitutionAdminView(
        Institution, db.session, endpoint=get_admin_view_endpoint(Institution)
    ),
    DocumentTypeAdminView(
        DocumentType, db.session, endpoint=get_admin_view_endpoint(DocumentType)
    ),
    OrganizationAdminView(
        Organization, db.session, endpoint=get_admin_view_endpoint(Organization)
    ),
    UserAdminView(User, db.session, endpoint=get_admin_view_endpoint(User)),
]
