import jwt
import pytz
from flask import Blueprint, Response, abort, render_template, url_for
from flask import current_app as app
from flask_login import current_user
from icalendar import Calendar
from icalendar import Event as ICalEvent

from database import db
from models.event import Event
from models.user import RolePermission, User
from utils.security import permission_check, secure_blueprint

blueprint = Blueprint("event", __name__, url_prefix="/events")
secure_blueprint(blueprint)


def _get_user_events(user: User):
    user_organizations = [x.id for x in user.get_organizations()]
    return (
        db.session.query(Event)
        .filter(Event.organization_id.in_(user_organizations))
        .all()
    )


@blueprint.route("/view/<int:event_id>")
def view(event_id: int):
    event = db.session.query(Event).get(event_id)
    if not event:
        return abort(404)
    if not permission_check(event, RolePermission.VIEW):
        return abort(403)

    return render_template("docdb/view_event.html", event=event)


@blueprint.route("/calendar")
def calendar():
    jwt_token = jwt.encode({"user_id": current_user.id}, app.config["SECRET_KEY"])
    icalendar_url = url_for("icalendar_all", jwt_token=jwt_token, _external=True)
    return render_template(
        "docdb/event_calendar.html",
        events=_get_user_events(current_user),
        icalendar_url=icalendar_url,
    )


@app.route("/events/icalendar/all/<string:jwt_token>")
def icalendar_all(jwt_token: str):
    try:
        decoded = jwt.decode(jwt_token, app.config["SECRET_KEY"], algorithms=["HS256"])
    except Exception:
        return abort(403)

    user = decoded["user_id"]
    user: User = db.session.query(User).get(user)
    if not user or not user.is_active:
        return abort(404)

    events = _get_user_events(user)
    cal = Calendar()

    for event in events:
        ical_event = ICalEvent()
        ical_event.add("uid", event.id)
        ical_event.add("summary", event.title)
        utc_date = event.date.replace(tzinfo=pytz.UTC)
        ical_event.add("dtstart", utc_date)
        description = ", ".join([str(x) for x in event.topics])
        ical_event.add("description", description)
        if event.location:
            ical_event.add("location", event.location)
        if event.event_url:
            ical_event.add("url", event.event_url)
        cal.add_component(ical_event)

    response = Response(cal.to_ical(), mimetype="text/calendar")
    response.headers["Content-Disposition"] = "attachment; filename=all_events.ics"
    return response
