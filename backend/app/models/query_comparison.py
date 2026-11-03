from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class QueryComparison(Base):
    __tablename__ = "query_comparisons"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    query_a: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    query_b: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    query_a_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    query_b_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    query_a_rows_examined: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    query_b_rows_examined: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    faster_query: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    speedup_percentage: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
