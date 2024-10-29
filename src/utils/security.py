from flask import Blueprint
from flask_login import current_user, login_required

from database import Model
from models.document import Document
from models.user import RolePermission, User


def secure_blueprint(blueprint: Blueprint):
    @blueprint.before_request
    @login_required
    def _():
        pass


def _roles_have_permission(user: User, permission: RolePermission):
    for role in user.roles:
        if permission.value in role.permissions:
            return True
    return False


def permission_check(model: Model, action: RolePermission):
    user: User | None = current_user  # type: ignore
    if not user or not user.is_authenticated:
        return False

    if isinstance(model, Document):
        if model.user_id == user.id and action == RolePermission.EDIT:
            action = RolePermission.EDIT_SELF

    return _roles_have_permission(user, action)
