from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc

from ..database import db
from ..models.user import RolePermission
from ..models.wiki import WikiPage, WikiRevision
from ..utils.security import permission_check, secure_blueprint

blueprint = Blueprint("wiki", __name__, url_prefix="/wiki")
secure_blueprint(blueprint)


@blueprint.route("/")
@login_required
def index():
    """List all wiki pages with hierarchical structure."""
    top_pages = (
        db.session.query(WikiPage)
        .filter(WikiPage.parent_id.is_(None))
        .order_by(WikiPage.title)
        .all()
    )
    return render_template("docdb/wiki/index.html", top_pages=top_pages)


@blueprint.route("/<slug>")
@login_required
def view_page(slug):
    """View a specific wiki page."""
    page = db.session.query(WikiPage).filter_by(slug=slug).first()
    if not page:
        return redirect(url_for("errors.error_404"))

    if not permission_check(page, RolePermission.VIEW):
        return redirect(url_for("index.no_role"))

    breadcrumbs = _get_breadcrumbs(page)
    can_edit = permission_check(page, RolePermission.EDIT)

    return render_template(
        "docdb/wiki/view.html",
        page=page,
        breadcrumbs=breadcrumbs,
        can_edit=can_edit,
    )


@blueprint.route("/new", methods=["GET", "POST"])
@login_required
def new_page():
    """Create a new wiki page."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip()
        content = request.form.get("content", "")
        parent_id = request.form.get("parent_id", type=int)

        # Validate required fields
        if not title or not slug:
            return render_template(
                "docdb/wiki/edit.html",
                error="Title and slug are required",
                title=title,
                slug=slug,
                content=content,
                parent_id=parent_id,
                all_pages=_get_all_pages(),
            )

        # Check if slug already exists
        existing = db.session.query(WikiPage).filter_by(slug=slug).first()
        if existing:
            return render_template(
                "docdb/wiki/edit.html",
                error=f"A page with slug '{slug}' already exists",
                title=title,
                slug=slug,
                content=content,
                parent_id=parent_id,
                all_pages=_get_all_pages(),
            )

        # Check parent exists if specified
        parent_page = None
        if parent_id:
            parent_page = db.session.query(WikiPage).get(parent_id)
            if not parent_page:
                parent_id = None

        # Create page
        page = WikiPage(
            title=title,
            slug=slug,
            parent_id=parent_id,
            content=content,
            organization_id=None,  # Or set based on user's org
        )

        # Create initial revision
        revision = WikiRevision(
            page=page,
            author_id=current_user.id,
            content=content,
            comment="Initial revision",
        )

        db.session.add(page)
        db.session.add(revision)
        db.session.commit()

        return redirect(url_for("wiki.view_page", slug=page.slug))

    # GET request - show form
    parent_id = request.args.get("parent", type=int)
    return render_template(
        "docdb/wiki/edit.html",
        page=None,
        parent_id=parent_id,
        all_pages=_get_all_pages(),
    )


@blueprint.route("/<slug>/edit", methods=["GET", "POST"])
@login_required
def edit_page(slug):
    """Edit an existing wiki page."""
    page = db.session.query(WikiPage).filter_by(slug=slug).first()
    if not page:
        return redirect(url_for("errors.error_404"))

    if not permission_check(page, RolePermission.EDIT):
        return redirect(url_for("index.no_role"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "")
        parent_id = request.form.get("parent_id", type=int)

        if not title:
            return render_template(
                "docdb/wiki/edit.html",
                page=page,
                error="Title is required",
                title=title,
                content=content,
                parent_id=parent_id,
                all_pages=_get_all_pages(),
            )

        # Check for circular parent reference
        if parent_id and parent_id == page.id:
            return render_template(
                "docdb/wiki/edit.html",
                page=page,
                error="Page cannot be its own parent",
                title=title,
                content=content,
                parent_id=parent_id,
                all_pages=_get_all_pages(),
            )

        # Validate parent exists
        parent_page = None
        if parent_id:
            parent_page = db.session.query(WikiPage).get(parent_id)
            if not parent_page:
                parent_id = None

        # Update page
        page.title = title
        page.parent_id = parent_id
        page.content = content

        # Create revision
        revision = WikiRevision(
            page=page,
            author_id=current_user.id,
            content=content,
            comment=request.form.get("comment", ""),
        )
        db.session.add(revision)
        db.session.commit()

        return redirect(url_for("wiki.view_page", slug=page.slug))

    # GET request - show form pre-populated
    return render_template(
        "docdb/wiki/edit.html", page=page, all_pages=_get_all_pages()
    )


@blueprint.route("/<slug>/history")
@login_required
def history(slug):
    """View revision history for a page."""
    page = db.session.query(WikiPage).filter_by(slug=slug).first()
    if not page:
        return redirect(url_for("errors.error_404"))

    if not permission_check(page, RolePermission.VIEW):
        return redirect(url_for("index.no_role"))

    revisions = page.revisions
    return render_template(
        "docdb/wiki/history.html",
        page=page,
        revisions=revisions,
    )


@blueprint.route("/<slug>/revision/<int:revision_id>")
@login_required
def view_revision(slug, revision_id):
    """View a specific revision of a page."""
    page = db.session.query(WikiPage).filter_by(slug=slug).first()
    if not page:
        return redirect(url_for("errors.error_404"))

    if not permission_check(page, RolePermission.VIEW):
        return redirect(url_for("index.no_role"))

    revision = (
        db.session.query(WikiRevision)
        .filter_by(id=revision_id, page_id=page.id)
        .first()
    )
    if not revision:
        return redirect(url_for("errors.error_404"))

    return render_template(
        "docdb/wiki/view_revision.html",
        page=page,
        revision=revision,
    )


def _get_all_pages() -> list[WikiPage]:
    """Get all wiki pages for parent selection."""
    return db.session.query(WikiPage).order_by(WikiPage.title).all()


def _get_breadcrumbs(page: WikiPage) -> list[WikiPage]:
    """Build breadcrumb trail from page up to root."""
    breadcrumbs = []
    current = page
    while current:
        breadcrumbs.insert(0, current)
        current = current.parent_page
    return breadcrumbs
