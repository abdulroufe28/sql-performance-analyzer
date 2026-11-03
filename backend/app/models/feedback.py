from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        default="GENERAL",
        nullable=False,
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )

    comment: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
