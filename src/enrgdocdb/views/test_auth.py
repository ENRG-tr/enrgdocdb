from flask import Blueprint
from flask_login import current_user

blueprint = Blueprint("test_auth", __name__, url_prefix="/test-auth")


@blueprint.route("/")
def index():
    if current_user.is_authenticated:
        return "You are logged in as '{}'".format(current_user.email)
    return "You are not logged in", 401


@blueprint.route("/has-role/<role>")
def has_role(role):
    if current_user.is_authenticated:
        if any(role in r.name for r in current_user.roles):
            return "You have the role '{}'".format(role)
    return "You do not have the role '{}'".format(role), 401
