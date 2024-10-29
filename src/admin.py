from flask import redirect, url_for
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.theme import Bootstrap4Theme
from wtforms import TextAreaField

from database import db
from models.author import Author, Institution
from models.document import Document
from models.topic import Topic

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


def get_admin_view_endpoint(model):
    return f"admin_{model.__name__}"


views = [
    DocumentAdminView(Document, db.session, endpoint=get_admin_view_endpoint(Document)),
    TopicAdminView(Topic, db.session, endpoint=get_admin_view_endpoint(Topic)),
    AuthorAdminView(Author, db.session, endpoint=get_admin_view_endpoint(Author)),
    InstitutionAdminView(
        Institution, db.session, endpoint=get_admin_view_endpoint(Institution)
    ),
]
