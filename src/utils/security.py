from flask import Blueprint
from flask_login import login_required


def secure_blueprint(blueprint: Blueprint):
    @blueprint.before_request
    @login_required
    def _():
        pass
