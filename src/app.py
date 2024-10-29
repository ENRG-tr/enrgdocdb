from flask import Flask
from flask_alembic import Alembic
from flask_babel import Babel
from flask_bootstrap import Bootstrap5
from flask_security.core import Security
from flask_security.datastore import FSQLALiteUserDatastore

from database import Model, db
from models.user import Role, User

alembic = Alembic(metadatas=Model.metadata)
user_datastore = FSQLALiteUserDatastore(db, User, Role)

security = Security()
babel = Babel()
bootstrap = Bootstrap5()


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

        for view in admin_views:
            admin.add_view(view)

    return app
