from flask import Blueprint, Response
from flask_login import current_user

blueprint = Blueprint("test_auth", __name__, url_prefix="/test-auth")


@blueprint.route("/")
def index():
    if current_user.is_authenticated:
        return "You are logged in as '{}'".format(current_user.email)
    return "You are not logged in", 401


@blueprint.route("/has-role/<role>")
def has_role(role):
    if not current_user.is_authenticated or not any(
        role in r.name for r in current_user.roles
    ):
        return Response(
            status=401, response="You do not have the role '{}'".format(role)
        )

    return Response(status=200, response="You have the role '{}'".format(role))


@blueprint.route("/has-role/<role>/with-admin-role/<admin_role>")
def has_role_with_admin_role(role, admin_role):
    res = has_role(role)
    if res.status_code == 401:
        return res

    response = Response(status=200, response="You have the role '{}'".format(role))
    response.headers["X-Admin-Access"] = (
        "1" if any(admin_role in r.name for r in current_user.roles) else "0"
    )

    return response
