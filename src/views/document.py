from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import or_

from database import db
from models.document import Document

blueprint = Blueprint("document", __name__)


@blueprint.route("/quick-search", methods=["GET"])
def quick_search():
    query = request.args.get("query", "")
    if query.strip() == "":
        return redirect(url_for("index.index"))

    documents = (
        db.session.query(Document)
        .filter(
            or_(
                Document.title.like(f"%{query}%"),
            )
        )
        .all()
    )
    return render_template(
        "docdb/quick_search.html", documents=documents, search_query=query
    )
