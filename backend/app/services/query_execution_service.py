from time import perf_counter
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Result

from backend.app.core.database import analysis_engine
from backend.app.services.explain_service import get_explain_plan
from backend.app.services.sql_safety_service import validate_read_only_sql


def execute_read_only_query(query: str, include_explain: bool = True) -> dict[str, Any]:
    """
    Executes a read-only query against the controlled analysis DB.
    Measures true execution time, captures row count, and attaches EXPLAIN analysis
    and evidence-based optimization recommendations.
    """
    safe_query = validate_read_only_sql(query)

    start_time = perf_counter()

    with analysis_engine.connect() as connection:
        result: Result = connection.execute(text(safe_query))
        rows = result.mappings().all()

    end_time = perf_counter()

    execution_time_ms = round((end_time - start_time) * 1000, 3)
    total_row_count = len(rows)
    # Preview up to 50 rows to prevent massive payloads over JSON
    preview_rows = [dict(row) for row in rows[:50]]

    payload: dict[str, Any] = {
        "query": safe_query,
        "execution_time_ms": execution_time_ms,
        "row_count": total_row_count,
        "rows": preview_rows,
    }

    if include_explain:
        explain_info = get_explain_plan(safe_query)
        payload.update(explain_info)

    return payload
