from flask import Blueprint, abort, flash, render_template, request
from flask import current_app as app
from flask_login import current_user

from database import db
from forms.user import EditUserProfileForm
from models.document import Document, DocumentFile
from models.user import RolePermission, User
from utils.pagination import paginate
from utils.security import permission_check, secure_blueprint

blueprint = Blueprint("user", __name__, url_prefix="/user")
secure_blueprint(blueprint)


@app.context_processor
def inject_permission_check():
    return dict(permission_check=permission_check, RolePermission=RolePermission)


@blueprint.route("/your_account", methods=["GET", "POST"])
def your_account():
    form = EditUserProfileForm()
    form.email.data = current_user.email

    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        db.session.commit()
        flash("Profile updated successfully")
    else:
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name

    return render_template("docdb/your_account.html", form=form)


@blueprint.route("/view/<int:user_id>")
def view(user_id: int):
    user = db.session.query(User).get(user_id)
    if not user:
        return abort(404)

    documents = paginate(
        db.session.query(Document).filter(Document.user_id == user_id),
        request,
    )
    files = paginate(
        db.session.query(DocumentFile)
        .join(Document, DocumentFile.document_id == Document.id)
        .filter(Document.user_id == user_id),
        request,
    )

    return render_template(
        "docdb/view_user.html", user=user, documents=documents, files=files
    )


@blueprint.route("/view/all", methods=["GET"])
def view_all():
    users = paginate(db.session.query(User), request)

    return render_template("docdb/view_user.html", users=users)
