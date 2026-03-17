from flask import Blueprint, abort, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from ..database import db
from ..models.user import RolePermission
from ..models.wiki import WikiFile, WikiPage, WikiRevision
from ..settings import FILE_UPLOAD_FOLDER
from ..utils.file import handle_user_file_upload
from ..utils.security import permission_check, secure_blueprint

blueprint = Blueprint("wiki", __name__, url_prefix="/wiki")
secure_blueprint(blueprint)


@blueprint.route("/")
@login_required
def index():
    """List all wiki pages with hierarchical structure."""
    # Get pinned pages first, then by title
    pinned_pages = (
        db.session.query(WikiPage)
        .filter(WikiPage.is_pinned == True)  # noqa: E712
        .order_by(WikiPage.title)
        .all()
    )
    # Filter pinned pages by permission
    pinned_pages = [
        p for p in pinned_pages if permission_check(p, RolePermission.VIEW)
    ]

    # Get all non-pinned pages
    all_pages = (
        db.session.query(WikiPage)
        .filter(WikiPage.is_pinned == False)  # noqa: E712
        .order_by(WikiPage.title)
        .all()
    )
    # Filter all pages by permission
    all_pages = [p for p in all_pages if permission_check(p, RolePermission.VIEW)]

    # Build hierarchical structure
    page_tree = build_page_tree(all_pages)

    # Check if user can edit any wiki page
    can_edit = permission_check(None, RolePermission.ADD)

    return render_template(
        "docdb/wiki/index.html",
        pinned_pages=pinned_pages,
        page_tree=page_tree,
        can_edit=can_edit,
    )


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
    can_admin = permission_check(page, RolePermission.ADMIN)

    return render_template(
        "docdb/wiki/view.html",
        page=page,
        breadcrumbs=breadcrumbs,
        can_edit=can_edit,
        can_admin=can_admin,
    )


@blueprint.route("/new", methods=["GET", "POST"])
@login_required
def new_page():
    """Create a new wiki page."""
    user_files_result = handle_user_file_upload(request)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip()
        parent_id = request.form.get("parent_id", type=int)
        is_pinned = request.form.get("is_pinned") == "true"
        content = request.form.get("content", "")

        # Validate required fields
        if not title or not slug:
            return render_template(
                "docdb/wiki/edit.html",
                error="Title and slug are required",
                title=title,
                slug=slug,
                parent_id=parent_id,
                is_pinned=is_pinned,
                content=content,
                all_pages=_get_all_pages(),
                user_files=user_files_result.template_args,
            )

        # Check if slug already exists
        existing = db.session.query(WikiPage).filter_by(slug=slug).first()
        if existing:
            return render_template(
                "docdb/wiki/edit.html",
                error=f"A page with slug '{slug}' already exists",
                title=title,
                slug=slug,
                parent_id=parent_id,
                is_pinned=is_pinned,
                content=content,
                all_pages=_get_all_pages(),
                user_files=user_files_result.template_args,
            )

        # Check parent exists if specified
        if parent_id:
            parent_page = db.session.query(WikiPage).get(parent_id)
            if not parent_page:
                parent_id = None

        # Create page
        page = WikiPage(
            title=title,
            slug=slug,
            is_pinned=is_pinned,
            parent_id=parent_id,
            content=content,
            organization_id=None,
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

        # Handle user files
        if user_files_result.user_files:
            for user_file in user_files_result.user_files:
                wiki_file = WikiFile(
                    page=page,
                    file_name=user_file.uploaded_file_name,
                    real_file_name=user_file.file_path,
                )
                db.session.add(wiki_file)

        db.session.commit()

        return redirect(url_for("wiki.view_page", slug=page.slug))

    # GET request - show form
    parent_id = request.args.get("parent", type=int)
    return render_template(
        "docdb/wiki/edit.html",
        page=None,
        parent_id=parent_id,
        all_pages=_get_all_pages(),
        user_files=user_files_result.template_args,
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

    user_files_result = handle_user_file_upload(request)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip()
        parent_id = request.form.get("parent_id", type=int)
        is_pinned = request.form.get("is_pinned") == "true"
        content = request.form.get("content", "")

        if not title:
            return render_template(
                "docdb/wiki/edit.html",
                page=page,
                error="Title is required",
                title=title,
                slug=slug,
                parent_id=parent_id,
                is_pinned=is_pinned,
                content=content,
                all_pages=_get_all_pages(),
                user_files=user_files_result.template_args,
            )

        # Check for slug conflict (excluding current page)
        if slug != page.slug:
            existing = db.session.query(WikiPage).filter_by(slug=slug).first()
            if existing:
                return render_template(
                    "docdb/wiki/edit.html",
                    page=page,
                    error=f"A page with slug '{slug}' already exists",
                    title=title,
                    slug=slug,
                    parent_id=parent_id,
                    is_pinned=is_pinned,
                    content=content,
                    all_pages=_get_all_pages(),
                    user_files=user_files_result.template_args,
                )

        # Check for circular parent reference
        if parent_id and parent_id == page.id:
            return render_template(
                "docdb/wiki/edit.html",
                page=page,
                error="Page cannot be its own parent",
                title=title,
                slug=slug,
                parent_id=parent_id,
                is_pinned=is_pinned,
                content=content,
                all_pages=_get_all_pages(),
                user_files=user_files_result.template_args,
            )

        # Validate parent exists
        if parent_id:
            parent_page = db.session.query(WikiPage).get(parent_id)
            if not parent_page:
                parent_id = None

        # Update page
        page.title = title
        page.slug = slug
        page.is_pinned = is_pinned
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

        # Handle user files
        if user_files_result.user_files:
            for user_file in user_files_result.user_files:
                wiki_file = WikiFile(
                    page=page,
                    file_name=user_file.uploaded_file_name,
                    real_file_name=user_file.file_path,
                )
                db.session.add(wiki_file)

        db.session.commit()

        return redirect(url_for("wiki.view_page", slug=page.slug))

    # GET request - show form pre-populated
    return render_template(
        "docdb/wiki/edit.html",
        page=page,
        all_pages=_get_all_pages(),
        user_files=user_files_result.template_args,
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


@blueprint.route("/download-file/<int:file_id>")
@login_required
def download_file(file_id: int):
    """Download an attached file."""
    file = db.session.query(WikiFile).get(file_id)
    if not file:
        return abort(404)

    if not permission_check(file.page, RolePermission.VIEW):
        return abort(403)

    if FILE_UPLOAD_FOLDER is None:
        return abort(500)

    return send_from_directory(
        FILE_UPLOAD_FOLDER,
        file.real_file_name,
        download_name=file.file_name,
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

    # Calculate relative revision number
    revision_number = (
        db.session.query(WikiRevision)
        .filter(
            WikiRevision.page_id == page.id,
            WikiRevision.id <= revision.id,
        )
        .count()
    )

    return render_template(
        "docdb/wiki/view_revision.html",
        page=page,
        revision=revision,
        revision_number=revision_number,
    )


@blueprint.route("/<slug>/delete", methods=["POST"])
@login_required
def delete_page(slug):
    """Delete a wiki page."""
    page = db.session.query(WikiPage).filter_by(slug=slug).first()
    if not page:
        return redirect(url_for("errors.error_404"))

    if not permission_check(page, RolePermission.EDIT):
        return redirect(url_for("index.no_role"))

    # Delete the page and all its children recursively
    db.session.delete(page)
    db.session.commit()

    return redirect(url_for("wiki.index"))


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


def build_page_tree(pages: list[WikiPage]) -> list[WikiPage]:
    """Build hierarchical tree structure from flat list of pages."""
    # Create a mapping of pages by their ID
    page_map = {page.id: page for page in pages}

    # Find root pages (those without parents or whose parent isn't in our list)
    roots = []
    for page in pages:
        if page.parent_id is None or page.parent_id not in page_map:
            roots.append(page)

    # Sort roots by title
    roots.sort(key=lambda x: x.title)

    # Build the tree by recursively organizing children
    def attach_children(parent_page: WikiPage):
        children = []
        for page in pages:
            if (
                page.parent_id == parent_page.id and page.id != parent_page.id
            ):  # Avoid self-reference
                children.append(page)
        # Sort children by title
        children.sort(key=lambda x: x.title)
        # Recursively attach grandchildren
        for child in children:
            attach_children(child)
        # Set the children on the parent
        parent_page.child_pages = children

    for root in roots:
        attach_children(root)

    return roots
