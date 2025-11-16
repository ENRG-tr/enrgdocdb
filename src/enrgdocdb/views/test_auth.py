from flask import Blueprint, render_template
from flask_login import current_user

from ..utils.security import secure_blueprint

blueprint = Blueprint("test_auth", __name__, url_prefix="/test-auth")
secure_blueprint(blueprint)


@blueprint.route("/")
def index():
    if current_user.is_authenticated:
        return "You are logged in as '{}'".format(current_user.email)
    return "You are not logged in", 401
