from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings


app_engine = create_engine(
    settings.app_database_url,
    pool_pre_ping=True,
)

analysis_engine = create_engine(
    settings.analysis_database_url,
    pool_pre_ping=True,
)

AppSessionLocal = sessionmaker(
    bind=app_engine,
    autoflush=False,
    autocommit=False,
)

AnalysisSessionLocal = sessionmaker(
    bind=analysis_engine,
    autoflush=False,
    autocommit=False,
)