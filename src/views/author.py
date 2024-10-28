from flask import Blueprint, abort, render_template, request

from database import db
from models.author import Author
from models.document import Document, DocumentAuthor
from utils.pagination import paginate
from utils.security import secure_blueprint

blueprint = Blueprint("author", __name__, url_prefix="/author")
secure_blueprint(blueprint)


@blueprint.route("/view/<int:author_id>")
def view(author_id: int):
    author = db.session.query(Author).get(author_id)
    if not author:
        return abort(404)

    documents = paginate(
        db.session.query(Document)
        .join(DocumentAuthor, Document.id == DocumentAuthor.document_id)
        .join(Author, DocumentAuthor.author_id == Author.id)
        .filter(Author.id == author_id),
        request,
    )

    return render_template("docdb/view_author.html", author=author, documents=documents)
