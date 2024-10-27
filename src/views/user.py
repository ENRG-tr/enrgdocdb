from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from database import db
from forms.user import EditUserProfileForm

blueprint = Blueprint("user", __name__)


@blueprint.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = EditUserProfileForm()
    form.email.data = current_user.email

    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        db.session.commit()
        flash("Profile updated successfully")
    else:
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name

    return render_template("docdb/profile.html", form=form)
