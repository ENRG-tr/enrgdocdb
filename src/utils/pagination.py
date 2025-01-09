from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from flask import Request
from flask_login import current_user
from sqlalchemy.orm import Query, Session

from database import db
from models.document import Document
from models.topic import Topic
from models.user import RolePermission
from utils.security import _is_super_admin
from utils.url import get_request_base_url


@dataclass
class PaginatedQueryResult:
    result: list
    page: int
    total_pages: int
    total_count: int
    query_name: str
    query_model: str

    def build_url(self, page: int, request: Request) -> str:
        query_dict: Any = dict(request.args)
        query_dict[self.query_name] = str(page)
        # convert query_dict to url params
        query_dict = urlencode(query_dict)
        return f"{get_request_base_url()}?{query_dict}"


def secure_query(query: Query, query_model: Any, user: Any, session: Session) -> Query:
    # Poison the query if the user does not exist
    if user is None or not user.is_authenticated:
        return query.filter(query_model.id == -1)
    if _is_super_admin(user):
        return query

    user_organizations = [
        role.organization_id
        for role in user.roles
        if RolePermission.VIEW in role.permissions
    ]

    if hasattr(query_model, "organization_id"):
        query = query.filter(query_model.organization_id.in_(user_organizations))
    if hasattr(query_model, "document") or hasattr(query_model, "document_id"):
        document_id = (
            getattr(query_model, "document_id", None) or query_model.document.id
        )
        # Don't join Document if it's already joined
        if (
            not isinstance(query_model, Document)
            and hasattr(query, "_last_joined_entity")
            and (
                query._last_joined_entity is None  # type: ignore
                or (
                    hasattr(query._last_joined_entity, "name")
                    and "documents" not in query._last_joined_entity.name  # type: ignore
                )
            )
        ):
            query = query.join(Document, Document.id == document_id)
        query = query.filter(Document.organization_id.in_(user_organizations))

    return query


def _filter_query(query: Query, query_model: Any) -> Query:
    if hasattr(query_model, "deleted_at"):
        query = query.filter(query_model.deleted_at == None)  # noqa: E711
    return query


def _sort_query(query: Query, query_model: Any) -> Query:
    if isinstance(query_model, Topic):
        query = query.order_by(Topic.parent_topic_id, Topic.id)
        return query

    if hasattr(query_model, "updated_at"):
        query = query.order_by(query_model.updated_at.desc())
    if hasattr(query_model, "created_at"):
        query = query.order_by(query_model.created_at.desc())
    return query


def paginate(
    query: Query, request: Request, per_page: int = 50, query_name: str | None = None
) -> PaginatedQueryResult:
    query_model: Any = query.column_descriptions[0]["entity"]

    query = secure_query(query, query_model, current_user, db.session)
    query = _filter_query(query, query_model)
    query = _sort_query(query, query_model)
    query_count = query.count()
    query = query.limit(per_page)
    if query_name is None:
        query_name = f"{query_model.__tablename__}_page"
    page = request.args.get(query_name, 1, type=int)
    query = query.offset((page - 1) * per_page)
    return PaginatedQueryResult(
        result=query.all(),
        page=page,
        total_count=query_count,
        total_pages=query_count // per_page,
        query_name=query_name,
        query_model=query_model.__name__,
    )
