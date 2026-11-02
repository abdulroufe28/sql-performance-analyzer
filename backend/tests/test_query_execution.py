import pytest

from backend.app.services.query_execution_service import (
    execute_read_only_query,
)
from backend.app.services.sql_safety_service import SQLSafetyError


def test_execute_select_query():
    result = execute_read_only_query(
        "SELECT * FROM customers"
    )

    assert result["row_count"] == 5
    assert result["execution_time_ms"] >= 0
    assert len(result["rows"]) == 5


def test_execute_delete_query_is_blocked():
    with pytest.raises(SQLSafetyError):
        execute_read_only_query(
            "DELETE FROM customers"
        )


def test_execute_multiple_statements_is_blocked():
    with pytest.raises(SQLSafetyError):
        execute_read_only_query(
            "SELECT * FROM customers; DROP TABLE customers"
        )