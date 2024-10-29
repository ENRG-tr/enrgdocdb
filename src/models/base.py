from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column


class Base:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        onupdate=func.current_timestamp()
    )
    deleted_at: Mapped[datetime | None] = mapped_column()

    @property
    def modified_at(self) -> datetime:
        return self.updated_at or self.created_at
