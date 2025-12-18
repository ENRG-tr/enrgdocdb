from flask import Blueprint, abort, redirect, render_template, request, url_for

from ..database import db
from ..models.author import Author, Institution
from ..models.document import Document, DocumentFile, DocumentType
from ..models.event import Event
from ..models.topic import Topic
from ..models.user import Organization, Role, User
from ..utils.pagination import paginate
from ..utils.security import secure_blueprint

blueprint = Blueprint("view_all", __name__, url_prefix="/view_all")
secure_blueprint(blueprint)


VIEW_ALL_ALLOWED_MODELS = [
    Document,
    DocumentType,
    DocumentFile,
    Event,
    Author,
    Institution,
    Topic,
    User,
    Role,
    Organization,
]


@blueprint.route("/<string:model_name>")
def view_all(model_name: str):
    if model_name not in [model.__name__ for model in VIEW_ALL_ALLOWED_MODELS]:
        return abort(404)

    model = [
        model for model in VIEW_ALL_ALLOWED_MODELS if model.__name__ == model_name
    ][0]
    models = paginate(db.session.query(model), request)
    return render_template(
        "docdb/view_all.html", model_name=model.__name__, models=models
    )


@blueprint.route("/new/<string:model_name>")
def proxy_new(model_name: str):
    if model_name not in [model.__name__ for model in VIEW_ALL_ALLOWED_MODELS]:
        return abort(404)

    return redirect(
        url_for(f"admin_{model_name}.create_view", url=request.args.get("url"))
    )
