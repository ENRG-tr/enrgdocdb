from collections.abc import Callable
from typing import Any

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import func

from ..database import db
from ..models.user import Role, User
from ..settings import API_SECRET_TOKEN

blueprint = Blueprint("api", __name__, url_prefix="/api")


def require_api_token(f: Callable[..., Any]):
    """Decorator that validates a Bearer token in the Authorization header."""

    def decorated(*args: Any, **kwargs: Any):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response(
                status=401, response="Missing or malformed Authorization header"
            )

        token = auth_header[len("Bearer ") :]
        if not API_SECRET_TOKEN or token != API_SECRET_TOKEN:
            return Response(status=403, response="Invalid API token")

        return f(*args, **kwargs)

    return decorated


@blueprint.route("/users/with-role/<role_name>", methods=["GET"])
@require_api_token
def users_with_role(role_name: str):
    """Return all active, non-deleted users who have a role whose name matches
    the given `role_name` (case-insensitive).
    """

    users = (
        db.session.query(User)
        .join(User.roles)
        .filter(
            func.lower(Role.name) == role_name.lower(),
            User.active.is_(True),
            User.deleted_at.is_(None),
        )
        .all()
    )

    result = [
        {
            "id": user.id,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "email": user.email,
            "username": user.username,
        }
        for user in users
    ]

    return jsonify(result)
