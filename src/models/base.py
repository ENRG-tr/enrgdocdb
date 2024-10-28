from datetime import datetime

from sqlalchemy import TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column


class Base:
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)

    @property
    def modified_at(self) -> datetime:
        return self.updated_at or self.created_at
