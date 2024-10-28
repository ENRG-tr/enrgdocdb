from datetime import datetime

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import and_, or_

from database import db
from models.author import Author
from models.document import Document, DocumentAuthor, DocumentFile
from models.topic import Topic
from models.user import User
from utils.pagination import PaginatedQueryResult, paginate
from utils.security import secure_blueprint

blueprint = Blueprint("search", __name__, url_prefix="/search")
secure_blueprint(blueprint)


@blueprint.route("/", methods=["GET"])
def index():
    query = request.args.get("query", "")
    if query.strip() == "":
        return redirect(url_for("index.index"))

    def filter_query(query: str, fields):
        query_split = query.split(" ")
        res = []
        for word in query_split:
            res.append(or_(field.ilike(f"%{word}%") for field in fields))  # type: ignore
        return and_(*res)

    search_start = datetime.now()
    result_initial = {
        "documents": (
            db.session.query(Document)
            .join(Document.authors)
            .join(DocumentAuthor.author)
            .filter(
                filter_query(
                    query,
                    [
                        Document.title,
                        Author.first_name,
                        Author.last_name,
                    ],
                )
            )
        ),
        "authors": (
            db.session.query(Author).filter(
                filter_query(
                    query,
                    [
                        Author.first_name,
                        Author.last_name,
                    ],
                )
            )
        ),
        "topics": (
            db.session.query(Topic).filter(
                filter_query(
                    query,
                    [
                        Topic.name,
                    ],
                )
            )
        ),
        "users": (
            db.session.query(User).filter(
                filter_query(
                    query,
                    [
                        User.first_name,
                        User.last_name,
                        User.email,
                    ],
                )
            )
        ),
        "files": (
            db.session.query(DocumentFile).filter(
                filter_query(
                    query,
                    [
                        DocumentFile.file_name,
                    ],
                )
            )
        ),
    }
    result: dict = {
        key: paginate(value, request) for key, value in result_initial.items()
    }
    search = {
        "result": result,
        "result_count": sum(len(result.result) for result in result.values()),
        "time_taken": (datetime.now() - search_start).total_seconds(),
    }
    return render_template("docdb/quick_search.html", search=search, query=query)
