import jwt
from flask import Blueprint, Response
from flask_login import current_user

from ..settings import AUTH_JWT_SECRET_KEY

blueprint = Blueprint("test_auth", __name__, url_prefix="/test-auth")


@blueprint.route("/")
def index():
    if current_user.is_authenticated:
        response = Response("You are logged in as '{}'".format(current_user.email))
        # Add identity headers for reverse proxy / backend service integration
        response.headers["X-Forwarded-User"] = current_user.username
        response.headers["X-Forwarded-Email"] = current_user.email
        response.headers["X-Forwarded-Name"] = getattr(current_user, "name", "")
        response.headers["X-Forwarded-Groups"] = ",".join(r.name for r in current_user.roles)
        return response
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
    assert AUTH_JWT_SECRET_KEY is not None
    res = has_role(role)
    if res.status_code == 401:
        return res

    response = Response(status=200, response="You have the role '{}'".format(role))

    is_admin = any(admin_role in r.name for r in current_user.roles)
    token_payload = {
        "admin": is_admin,
        "user_info": {
            "id": current_user.id,
            "email": current_user.email,
            "name": getattr(current_user, "name", ""),
            "roles": [r.name for r in current_user.roles],
            "username": current_user.username,
        },
    }
    response.headers["X-Admin-Access"] = jwt.encode(token_payload, AUTH_JWT_SECRET_KEY)

    return response
