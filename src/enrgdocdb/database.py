from flask_security.models import sqla as sqla
from flask_sqlalchemy_lite import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase

from .utils.logging import get_logger

logger = get_logger(__name__)


class Model(DeclarativeBase):
    pass


db = SQLAlchemy()
sqla.FsModels.set_db_info(base_model=Model)

logger.info("Database module initialized")


def register_sql_logging():
    """Register SQL query logging event listeners (must be called after app creation)."""

    @event.listens_for(db.engine, "before_cursor_execute")
    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        """Log SQL queries in debug mode."""
        if logger.level <= 10:  # DEBUG level
            sql_str = str(statement)
            if len(sql_str) > 100:
                sql_str = sql_str[:100] + "..."
            logger.debug(f"SQL: {sql_str}")

    @event.listens_for(db.engine, "handle_error")
    def handle_error(error):
        """Log database errors."""
        logger.error(f"Database error: {error}", exc_info=True)


logger.debug("SQL logging registration function defined")
