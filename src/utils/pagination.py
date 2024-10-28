from dataclasses import dataclass
from typing import Any

from flask import Request, url_for
from sqlalchemy.orm import Query


@dataclass
class PaginatedQueryResult:
    result: list
    page: int
    total_pages: int
    query_name: str
    query_model: str

    def build_url(self, page: int, request: Request) -> str:
        query_dict: Any = dict(request.args)
        # Query name should not start with _ because then it can alter internal
        # variables of url_for
        assert not self.query_name.startswith("_"), "Query name cannot start with _"
        query_dict[self.query_name] = str(page)
        assert request.endpoint
        return url_for(request.endpoint, **query_dict)


def paginate(
    query: Query, request: Request, per_page: int = 50, query_name: str | None = None
) -> PaginatedQueryResult:
    query_count = query.count()
    query_model: Any = query.column_descriptions[0]["entity"]

    query = query.limit(per_page)
    if query_name is None:
        query_name = f"{query_model.__tablename__}_page"
    page = request.args.get(query_name, 1, type=int)
    query = query.offset((page - 1) * per_page)
    return PaginatedQueryResult(
        result=query.all(),
        page=page,
        total_pages=query_count // per_page,
        query_name=query_name,
        query_model=query_model.__name__,
    )
