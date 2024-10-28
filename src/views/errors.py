import traceback

from flask import current_app as app
from flask import render_template

blueprint = None


@app.errorhandler(404)
def handle_404(e):
    return render_template("docdb/errors/404.html"), 404


if not app.debug:

    @app.errorhandler(Exception)
    def handle_all(e: Exception):
        print("".join(traceback.format_exception(e)))
        return render_template("docdb/errors/all.html", exception=e), 500
