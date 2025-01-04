from flask import Blueprint, abort, render_template

from database import db
from models.event import Event
from models.user import RolePermission
from utils.security import permission_check, secure_blueprint

blueprint = Blueprint("event", __name__, url_prefix="/events")
secure_blueprint(blueprint)


@blueprint.route("/view/<int:event_id>")
def view(event_id: int):
    event = db.session.query(Event).get(event_id)
    if not event:
        return abort(404)
    if not permission_check(event, RolePermission.VIEW):
        return abort(403)

    return render_template("docdb/view_event.html", event=event)
