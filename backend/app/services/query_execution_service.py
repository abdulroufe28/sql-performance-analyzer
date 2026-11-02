from time import perf_counter

from sqlalchemy import text
from sqlalchemy.engine import Result

from backend.app.core.database import analysis_engine
from backend.app.services.sql_safety_service import validate_read_only_sql


def execute_read_only_query(query: str) -> dict:
    safe_query = validate_read_only_sql(query)

    start_time = perf_counter()

    with analysis_engine.connect() as connection:
        result: Result = connection.execute(text(safe_query))

        rows = result.mappings().all()

    end_time = perf_counter()

    execution_time_ms = (end_time - start_time) * 1000

    return {
        "query": safe_query,
        "execution_time_ms": round(execution_time_ms, 3),
        "row_count": len(rows),
        "rows": [dict(row) for row in rows],
    }