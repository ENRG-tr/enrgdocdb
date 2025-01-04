from datetime import datetime, timedelta

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from database import db
from models.document import Document
from models.event import Event
from utils.pagination import paginate
from utils.security import secure_blueprint
from views.view_all import VIEW_ALL_ALLOWED_MODELS

blueprint = Blueprint("index", __name__)
secure_blueprint(blueprint)


@blueprint.route("/")
@login_required
def index():
    documents_last_7_days = paginate(
        db.session.query(Document).where(
            or_(
                Document.updated_at > datetime.now() - timedelta(days=7),
                Document.created_at > datetime.now() - timedelta(days=7),
            )
        ),
        request,
    )
    last_events = db.session.query(Event).order_by(Event.date.desc()).limit(300).all()
    view_all_allowed_models = [model.__name__ for model in VIEW_ALL_ALLOWED_MODELS]
    return render_template(
        "docdb/index.html",
        documents_last_7_days=documents_last_7_days,
        events=last_events,
        view_all_allowed_models=view_all_allowed_models,
    )


@blueprint.route("/no-role")
def no_role():
    if len(current_user.roles):
        return redirect(url_for("index.index"))
    return render_template("docdb/no_role.html")
