from operator import or_

from flask import Blueprint, redirect, render_template, request, url_for

from database import db
from models.document import Document

blueprint = Blueprint("search", __name__, url_prefix="/search")


@blueprint.route("/", methods=["GET"])
def index():
    query = request.args.get("query", "")
    if query.strip() == "":
        return redirect(url_for("index.index"))

    documents = (
        db.session.query(Document).filter(Document.title.like(f"%{query}%")).all()
    )
    return render_template(
        "docdb/quick_search.html", documents=documents, search_query=query
    )
