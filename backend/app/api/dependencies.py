from collections.abc import Generator

from sqlalchemy.orm import Session

from backend.app.core.database import AppSessionLocal


def get_db() -> Generator[Session, None, None]:
    db = AppSessionLocal()

    try:
        yield db
    finally:
        db.close()