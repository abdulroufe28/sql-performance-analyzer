from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class QueryAnalysis(Base):
    __tablename__ = "query_analyses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    execution_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    query_cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    rows_examined: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    performance_rating: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    has_full_table_scan: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
