from typing import Any

from backend.app.services.query_execution_service import execute_read_only_query


def compare_queries(query_a: str, query_b: str) -> dict[str, Any]:
    """
    Executes and benchmarks two SQL queries side-by-side.
    Compares execution time, rows examined, index usage, and generates
    an evidence-based comparison verdict.
    """
    result_a = execute_read_only_query(query_a)
    result_b = execute_read_only_query(query_b)

    time_a = result_a["execution_time_ms"]
    time_b = result_b["execution_time_ms"]

    rows_examined_a = result_a.get("total_rows_examined", 0)
    rows_examined_b = result_b.get("total_rows_examined", 0)

    time_diff = round(abs(time_a - time_b), 3)

    if time_a < time_b:
        faster_query = "QUERY_A"
        speedup_pct = round(((time_b - time_a) / time_b * 100), 1) if time_b > 0 else 0.0
        multiplier = round(time_b / time_a, 1) if time_a > 0 else 1.0
        verdict = f"Query A is {multiplier}x faster ({speedup_pct}% speedup) than Query B."
    elif time_b < time_a:
        faster_query = "QUERY_B"
        speedup_pct = round(((time_a - time_b) / time_a * 100), 1) if time_a > 0 else 0.0
        multiplier = round(time_a / time_b, 1) if time_b > 0 else 1.0
        verdict = f"Query B is {multiplier}x faster ({speedup_pct}% speedup) than Query A."
    else:
        faster_query = "TIE"
        speedup_pct = 0.0
        verdict = "Both queries demonstrated virtually identical execution time."

    # Add index and scan context to the verdict
    if result_a.get("has_full_table_scan") and not result_b.get("has_full_table_scan"):
        verdict += " Query B eliminated the full table scan observed in Query A."
    elif result_b.get("has_full_table_scan") and not result_a.get("has_full_table_scan"):
        verdict += " Query A eliminated the full table scan observed in Query B."

    if rows_examined_a > rows_examined_b:
        verdict += f" Query B examined {rows_examined_a - rows_examined_b} fewer rows."
    elif rows_examined_b > rows_examined_a:
        verdict += f" Query A examined {rows_examined_b - rows_examined_a} fewer rows."

    return {
        "query_a": result_a,
        "query_b": result_b,
        "faster_query": faster_query,
        "time_diff_ms": time_diff,
        "speedup_percentage": speedup_pct,
        "rows_examined_diff": abs(rows_examined_a - rows_examined_b),
        "verdict": verdict,
    }
