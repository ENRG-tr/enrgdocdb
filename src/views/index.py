from flask import Blueprint, render_template
from flask_login import current_user, login_required

blueprint = Blueprint("index", __name__)


@blueprint.route("/")
@login_required
def index():
    return render_template("docdb/index.html", user=current_user)
