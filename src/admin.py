from flask import redirect, url_for
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.theme import Bootstrap4Theme
from wtforms import TextAreaField

from database import db
from models.document import Document

admin = Admin(
    name="ENRG DocDB Admin",
    theme=Bootstrap4Theme(base_template="docdb/admin/base.html"),
    index_view=None,
)


class AdminView(ModelView):
    # disable edit for created_at, updated_at, deleted_at
    form_excluded_columns = ["created_at", "updated_at", "deleted_at"]

    # disable list view and create view
    can_create = False

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


def get_admin_view_endpoint(model):
    return f"admin_{model.__name__}"


views = [
    DocumentAdminView(Document, db.session, endpoint=get_admin_view_endpoint(Document))
]
