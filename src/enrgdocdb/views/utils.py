from flask import current_app as app

from ..utils.url import get_request_base_url, get_request_url


@app.context_processor
def inject_url():
    return dict(
        get_request_url=get_request_url, get_request_base_url=get_request_base_url
    )
