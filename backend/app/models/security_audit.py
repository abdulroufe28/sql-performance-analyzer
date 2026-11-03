from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SecurityAuditLog(Base):
    __tablename__ = "security_audit_logs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    violation_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    attempted_query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    client_ip: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
