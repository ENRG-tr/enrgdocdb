from flask import Flask
from flask_admin import Admin
from flask_alembic import Alembic
from flask_babel import Babel
from flask_security import FSQLALiteUserDatastore, Security

from database import Model, db
from models.user import Role, User

alembic = Alembic(metadatas=Model.metadata)
user_datastore = FSQLALiteUserDatastore(db, User, Role)

admin = Admin()
security = Security()
babel = Babel()


def create_app():
    app = Flask(__name__)
    with app.app_context():
        app.config.from_pyfile("settings.py")
        for plugin in [admin, db, alembic, babel]:
            plugin.init_app(app)
        security.init_app(app, user_datastore)

    return app
