from flask import Blueprint, Response, request
from flask_login import current_user

blueprint = Blueprint("test_auth", __name__, url_prefix="/test-auth")


@blueprint.route("/")
def index():
    if current_user.is_authenticated:
        return "You are logged in as '{}'".format(current_user.email)
    return "You are not logged in", 401


@blueprint.route("/has-role/<role>")
def has_role(role):
    has_role_as_admin_access = request.args.get("has_role_as_admin_access")
    response = Response(
        status=401, response="You do not have the role '{}'".format(role)
    )
    if not current_user.is_authenticated or not any(
        role in r.name for r in current_user.roles
    ):
        return response

    response = Response(status=200, response="You have the role '{}'".format(role))
    if any(has_role_as_admin_access in r.name for r in current_user.roles):
        response.headers["X-Admin-Access"] = "1"

    return response
