from datetime import datetime, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import or_

from database import db
from models.document import Document
from utils.pagination import paginate

blueprint = Blueprint("index", __name__)


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
    return render_template(
        "docdb/index.html", documents_last_7_days=documents_last_7_days
    )
