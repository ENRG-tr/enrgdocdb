from flask import Blueprint, abort, render_template, request

from database import db
from models.author import Author, Institution
from models.document import Document, DocumentAuthor
from utils.pagination import paginate
from utils.security import secure_blueprint

blueprint = Blueprint("institution", __name__, url_prefix="/institution")
secure_blueprint(blueprint)


@blueprint.route("/view/<int:institution_id>")
def view(institution_id: int):
    institution = db.session.query(Institution).get(institution_id)
    if not institution:
        return abort(404)

    documents = paginate(
        db.session.query(Document)
        .join(DocumentAuthor, Document.id == DocumentAuthor.document_id)
        .join(Author, DocumentAuthor.author_id == Author.id)
        .filter(Author.institution_id == institution_id),
        request,
    )

    authors = paginate(
        db.session.query(Author).filter(Author.institution_id == institution_id),
        request,
    )

    return render_template(
        "docdb/view_institution.html",
        institution=institution,
        documents=documents,
        authors=authors,
    )
