from flask import Flask
from flask_alembic import Alembic
from flask_babel import Babel
from flask_bootstrap import Bootstrap5
from flask_security.core import Security
from flask_security.datastore import FSQLALiteUserDatastore

from database import Model, db
from models.user import Role, User
from settings import SECURITY_OAUTH_ENABLE_SLACK
from slack import SlackFsOauthProvider

alembic = Alembic(metadatas=Model.metadata)
user_datastore = FSQLALiteUserDatastore(db, User, Role)

security = Security()
babel = Babel()
bootstrap = Bootstrap5()


def monkeypatch_user_loader(user_loader):
    def _user_loader(*args, **kwargs):
        user = user_loader(*args, **kwargs)
        if user and user.deleted_at:
            return None
        return user

    return _user_loader


def create_app():
    app = Flask(__name__)
    with app.app_context():
        from views import get_blueprints

        for blueprint in get_blueprints():
            app.register_blueprint(blueprint)

        app.config.from_pyfile("settings.py")
        app.config.from_prefixed_env()

        for plugin in [db, alembic, babel, bootstrap]:
            plugin.init_app(app)
        from admin import admin
        from admin import views as admin_views

        admin.init_app(app)
        security.init_app(app, user_datastore)

        user_datastore.find_user = monkeypatch_user_loader(user_datastore.find_user)

        if SECURITY_OAUTH_ENABLE_SLACK and security.oauthglue:
            security.oauthglue.register_provider_ext(SlackFsOauthProvider("Slack"))

            @app.context_processor
            def inject_oauth_start_url():
                def get_slack_oauth_url():
                    return security.oauthglue.get_redirect("Slack").location  # type: ignore

                return dict(
                    get_slack_oauth_url=get_slack_oauth_url,
                )

        for view in admin_views:
            admin.add_view(view)

    return app
