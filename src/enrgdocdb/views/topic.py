from flask import Blueprint, abort, render_template, request

from ..database import db
from ..models.document import Document
from ..models.topic import Topic
from ..utils.pagination import paginate
from ..utils.security import secure_blueprint

blueprint = Blueprint("topic", __name__, url_prefix="/topic")
secure_blueprint(blueprint)


@blueprint.route("/view/<int:topic_id>")
def view(topic_id: int):
    topic = db.session.query(Topic).get(topic_id)
    if not topic:
        return abort(404)

    documents = paginate(
        db.session.query(Document).filter(Document.topics.any(id=topic_id)),
        request,
    )

    return render_template("docdb/view_topic.html", topic=topic, documents=documents)
