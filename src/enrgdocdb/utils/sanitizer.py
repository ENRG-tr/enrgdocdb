"""HTML sanitization utilities for XSS prevention."""

import bleach
from markupsafe import Markup

# Allowed tags for wiki content rendering
ALLOWED_TAGS = [
    "p",
    "br",
    "hr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "code",
    "kbd",
    "samp",
    "var",
    "em",
    "strong",
    "del",
    "s",
    "u",
    "a",
    "img",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "div",
    "span",
]

# Allowed attributes
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target"],
    "img": ["src", "alt", "title", "width", "height"],
    "th": ["scope", "colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
    "*": ["class", "id"],
}

# Allowed protocols for href and src attributes
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "ftp"]

# Allowed CSS properties (if using bleach-sanitize.css)
ALLOWED_CSS_PROPERTIES = [
    "color",
    "background-color",
    "font-size",
    "font-family",
    "font-weight",
    "font-style",
    "text-align",
    "vertical-align",
    "text-decoration",
    "border",
    "border-color",
    "border-style",
    "border-width",
    "margin",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "width",
    "height",
    "max-width",
    "max-height",
    "display",
    "visibility",
]

# Allowed CSS classes (whitelist approach for better security)
ALLOWED_CSS_CLASSES = [
    "text-muted",
    "text-primary",
    "fw-bold",
    "small",
    "scale-down-mobile",
    "bg-light",
    "border",
    "rounded",
    "position-relative",
    "text-truncate",
    "me-1",
    "mb-0",
    "mb-4",
    "mt-2",
    "p-2",
    "d-flex",
    "align-items-center",
    "text-uppercase",
    "text-decoration-none",
    "float-end",
    "gap-3",
    "flex-wrap",
    "list-unstyled",
    "me-2",
    "text-dark",
    "fw-bold",
    "text-danger",
    "text-warning",
    "text-success",
]


def sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Uses bleach to strip dangerous tags, attributes, and protocols while
    preserving a safe subset of HTML for wiki content rendering.

    Args:
        html_content: Raw HTML string to sanitize

    Returns:
        Sanitized HTML string
    """
    if not html_content:
        return html_content

    # Clean the HTML using bleach
    cleaned = bleach.clean(
        text=html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )

    return cleaned


def sanitize_html_for_jinja(html_content: str) -> Markup:
    """
    Sanitize HTML content and return as Markup for Jinja2 templates.

    This function is intended to be used as a Jinja2 filter. It sanitizes
    the HTML content and then wraps it in Markup to prevent Jinja2 from
    double-escaping it.

    Args:
        html_content: Raw HTML string to sanitize

    Returns:
        Markup object containing sanitized HTML
    """
    if not html_content:
        return Markup("")

    sanitized = sanitize_html(html_content)
    return Markup(sanitized)
