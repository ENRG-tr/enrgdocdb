import traceback

from flask import current_app as app
from flask import render_template, request

from ..utils.logging import get_logger

logger = get_logger(__name__)

blueprint = None


@app.errorhandler(404)
def handle_404(e):
    logger.warning(f"404 error: {request.path} - {request.method}")
    return render_template("docdb/errors/404.html"), 404


if not app.debug:

    @app.errorhandler(Exception)
    def handle_all(e: Exception):
        # Log the full exception with stack trace
        logger.error(
            f"Unhandled exception: {e}",
            exc_info=True,
            extra={
                'path': request.path,
                'method': request.method,
                'user_id': getattr(request, 'user_id', None),
            }
        )
        return render_template("docdb/errors/all.html", exception=e), 500
