import logging

from flask import Flask, request
from flask_alembic import Alembic
from flask_babel import Babel
from flask_bootstrap import Bootstrap5
from flask_limiter import Limiter
from flask_login import current_user
from flask_security.core import Security
from flask_security.datastore import FSQLALiteUserDatastore

from .database import Model, db, register_sql_logging
from .models.user import Role, User
from .oauth.slack import SlackFsOauthProvider
from .settings import SECURITY_OAUTH_ENABLE_SLACK
from .utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

alembic = Alembic(metadatas=Model.metadata)
user_datastore = FSQLALiteUserDatastore(db, User, Role)

security: Security = Security()
babel: Babel = Babel()
bootstrap: Bootstrap5 = Bootstrap5()
def limiter_keyfunc():
    """Get key for rate limiting (user ID or remote address)."""
    return str(current_user.id) if current_user else request.remote_addr or "unknown"

limiter = Limiter(key_func=limiter_keyfunc)


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
        logger.info("Starting ENRG DocDB application")
        
        from .views import get_blueprints

        for blueprint in get_blueprints():
            logger.debug(f"Registering blueprint: {blueprint.name}")
            app.register_blueprint(blueprint)

        app.config.from_pyfile("settings.py")
        app.config.from_prefixed_env()

        logger.debug(f"Configuration loaded: SECRET_KEY={'*' * 8 if app.config.get('SECRET_KEY') else 'MISSING'}")
        logger.info(f"Environment: {app.config.get('FLASK_ENV', 'development')}")

        for plugin in [db, alembic, babel, bootstrap]:
            logger.debug(f"Initializing plugin: {type(plugin).__name__}")
            plugin.init_app(app)
        
        # Register SQL logging after db is initialized
        logger.debug("Registering SQL query logging")
        register_sql_logging()
        
        from .admin import admin
        from .admin import views as admin_views

        admin.init_app(app)
        security.init_app(app, user_datastore)
        limiter.init_app(app)

        user_datastore.find_user = monkeypatch_user_loader(user_datastore.find_user)
        
        # Set up application-wide logging
        setup_logging(app)

        if SECURITY_OAUTH_ENABLE_SLACK and security.oauthglue:
            logger.info("Enabling Slack OAuth provider")
            security.oauthglue.register_provider_ext(SlackFsOauthProvider("Slack"))

            @app.context_processor
            def inject_oauth_start_url():
                def get_slack_oauth_url():
                    return security.oauthglue.get_redirect("Slack").location  # type: ignore

                return dict(
                    get_slack_oauth_url=get_slack_oauth_url,
                )
        else:
            logger.debug("Slack OAuth not enabled")

        logger.debug(f"Adding {len(admin_views)} admin views")
        for view in admin_views:
            admin.add_view(view)

        logger.info("Application initialization complete")

        @app.cli.command("run-ldap")
        def run_ldap():
            """Run the LDAP server."""
            from src.enrgdocdb.ldap_server import run_ldap_server

            run_ldap_server(app)

    return app
