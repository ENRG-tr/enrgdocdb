from typing import Any

from flask import Blueprint, redirect, request, url_for
from flask_login import current_user, login_required

from database import db
from models.document import Document
from models.user import RolePermission, User


def secure_blueprint(blueprint: Blueprint):
    @blueprint.before_request
    @login_required
    def _():
        pass

    @blueprint.before_request
    def __():
        if not len(current_user.roles) and request.endpoint != "index.no_role":
            return redirect(url_for("index.no_role"))


def _roles_have_permission(
    user: User, organization_id: int | None, permission: RolePermission
):
    for role in user.roles:
        # Sidenote: None organization_id means all organizations
        if (
            organization_id
            and role.organization_id
            and role.organization_id != organization_id
        ):
            continue

        if permission.value in role.permissions:
            return True
    return False


def _is_super_admin(user: User):
    for role in user.roles:
        if role.organization_id is None and RolePermission.ADMIN in role.permissions:
            return True
    return False


def permission_check(model: Any, action: RolePermission):
    user: User | None = current_user  # type: ignore
    if not user or not user.is_authenticated:
        return False
    if _is_super_admin(user):
        return True

    organization_id = None

    # Try to get the organization_id from the model
    if model:
        if isinstance(model, Document):
            organization_id = model.organization_id
            if model.user_id == user.id and action == RolePermission.EDIT:
                action = RolePermission.EDIT_SELF
        elif hasattr(model, "organization_id"):
            organization_id = model.organization_id
        elif hasattr(model, "document_id") or hasattr(model, "document"):
            if hasattr(model, "document"):
                organization_id = model.document.organization_id
            else:
                document = (
                    db.session.query(Document).filter_by(id=model.document_id).first()
                )
                if document:
                    organization_id = document.organization_id
        elif isinstance(model, User):
            has_permission = False
            for target_role in model.roles:
                if _roles_have_permission(user, target_role.organization_id, action):
                    has_permission = True

            return has_permission

        # If no organization_id is found, only allow VIEW
        if not organization_id and action == RolePermission.VIEW:
            return True

    return _roles_have_permission(user, organization_id, action)
