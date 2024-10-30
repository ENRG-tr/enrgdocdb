from urllib.parse import urlparse

from flask import request


def get_request_url():
    o = urlparse(request.url)
    return o.path + ("?" + o.query if o.query else "")


def get_request_base_url():
    o = urlparse(request.base_url)
    return o.path
