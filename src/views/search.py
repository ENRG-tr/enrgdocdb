from datetime import datetime

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import or_

from database import db
from models.author import Author
from models.document import Document, DocumentAuthor, DocumentFile
from models.topic import Topic
from models.user import User
from utils.security import secure_blueprint

blueprint = Blueprint("search", __name__, url_prefix="/search")
secure_blueprint(blueprint)


@blueprint.route("/", methods=["GET"])
def index():
    query = request.args.get("query", "")
    if query.strip() == "":
        return redirect(url_for("index.index"))
    search_start = datetime.now()
    result = {
        "documents": (
            db.session.query(Document)
            .join(Document.authors)
            .join(DocumentAuthor.author)
            .filter(
                or_(
                    Document.title.ilike(f"%{query}%"),
                    Author.first_name.ilike(f"%{query}%"),
                    Author.last_name.ilike(f"%{query}%"),
                )
            )
            .all()
        ),
        "authors": (
            db.session.query(Author)
            .filter(
                or_(
                    Author.first_name.ilike(f"%{query}%"),
                    Author.last_name.ilike(f"%{query}%"),
                )
            )
            .all()
        ),
        "topics": (
            db.session.query(Topic)
            .filter(
                or_(
                    Topic.name.ilike(f"%{query}%"),
                )
            )
            .all()
        ),
        "users": (
            db.session.query(User)
            .filter(
                or_(
                    User.first_name.ilike(f"%{query}%"),
                    User.last_name.ilike(f"%{query}%"),
                    User.email.ilike(f"%{query}%"),
                )
            )
            .all()
        ),
        "files": (
            db.session.query(DocumentFile)
            .filter(
                or_(
                    DocumentFile.file_name.ilike(f"%{query}%"),
                )
            )
            .all()
        ),
    }
    result["result_count"] = sum(len(result) for result in result.values())
    result["time_taken"] = (datetime.now() - search_start).total_seconds()
    return render_template("docdb/quick_search.html", result=result, query=query)
