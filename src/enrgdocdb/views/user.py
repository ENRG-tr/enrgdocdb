from typing import cast

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask import current_app as app
from flask_login import current_user
from flask_security.utils import hash_password

from ..app import user_datastore
from ..database import db
from ..forms.user import CreateUserForm, EditUserProfileForm
from ..models.document import Document, DocumentFile
from ..models.user import Organization, RolePermission, Role, User
from ..utils.pagination import paginate
from ..utils.security import permission_check, secure_blueprint
from ..utils.logging import get_logger

logger = get_logger(__name__)

blueprint = Blueprint("user", __name__, url_prefix="/user")
secure_blueprint(blueprint)


@app.context_processor
def inject_permission_check():
    return dict(permission_check=permission_check, RolePermission=RolePermission)


@blueprint.route("/your_account", methods=["GET", "POST"])
def your_account():
    form = EditUserProfileForm()
    user = cast(User, current_user)
    form.email.data = user.email
    form.username.data = user.username

    if form.validate_on_submit():
        logger.info(f"User {current_user.id} updating profile")  # type: ignore
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data

        if form.new_password.data:
            if form.new_password.data == form.confirm_password.data:
                logger.info(f"User {current_user.id} updated password")  # type: ignore
                user.password = hash_password(form.new_password.data)
                flash("Profile and account password updated successfully")
            else:
                flash("Passwords do not match", "error")
                logger.warning(f"User {current_user.id} entered mismatched passwords")  # type: ignore
        else:
            flash("Profile updated successfully")

        db.session.commit()
    else:
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name

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


@blueprint.route("/create", methods=["GET", "POST"])
def create():
    """Create a new user. Only administrators can create users."""

    def render():
        return render_template("docdb/create_user.html", form=form)

    if not permission_check(None, RolePermission.ADMIN):
        return abort(403)

    form = CreateUserForm()

    if form.validate_on_submit():
        try:
            # Create user using Flask-Security datastore
            user = db.session.query(User).filter_by(email=form.email.data).first()
            if user:
                flash("User with this email already exists", "error")
                return render()
            user = user_datastore.create_user(
                email=form.email.data,
                password=hash_password(form.password.data),
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                active=True,
            )

            # Add role to user
            role = db.session.query(Role).get(form.role.data)
            if role:
                user_datastore.add_role_to_user(user, role)

            db.session.commit()
            flash("User created successfully!", "success")
            return redirect(url_for("user.view", user_id=user.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating user: {str(e)}", "error")

    return render()
