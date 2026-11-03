import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.core.database import analysis_engine
from backend.app.services.anti_pattern_service import analyze_sql_anti_patterns
from backend.app.services.sql_safety_service import validate_read_only_sql


def _extract_tables_from_json(node: Any, tables: list[dict[str, Any]]) -> None:
    """Recursively traverses MySQL EXPLAIN JSON to extract all table nodes."""
    if isinstance(node, dict):
        if "table" in node and isinstance(node["table"], dict):
            tables.append(node["table"])
        for key, value in node.items():
            if key != "table":
                _extract_tables_from_json(value, tables)
    elif isinstance(node, list):
        for item in node:
            _extract_tables_from_json(item, tables)


def _check_flag_in_json(node: Any, flag_name: str) -> bool:
    """Recursively checks if a boolean flag like using_filesort or using_temporary_table is True."""
    if isinstance(node, dict):
        if node.get(flag_name) is True:
            return True
        return any(_check_flag_in_json(val, flag_name) for val in node.values())
    elif isinstance(node, list):
        return any(_check_flag_in_json(item, flag_name) for item in node)
    return False


def get_explain_plan(query: str) -> dict[str, Any]:
    """
    Executes EXPLAIN and EXPLAIN FORMAT=JSON against the controlled analysis DB.
    Parses execution metrics, identifies performance bottlenecks, and generates
    evidence-based optimization recommendations.
    """
    safe_query = validate_read_only_sql(query)

    with analysis_engine.connect() as connection:
        # 1. Run Tabular EXPLAIN
        tabular_result = connection.execute(text(f"EXPLAIN {safe_query}")).mappings().all()
        tabular_plan = [dict(row) for row in tabular_result]

        # 2. Run JSON EXPLAIN
        json_result = connection.execute(text(f"EXPLAIN FORMAT=JSON {safe_query}")).mappings().all()
        raw_json_str = json_result[0]["EXPLAIN"]
        json_plan = json.loads(raw_json_str)

    query_block = json_plan.get("query_block", {})
    cost_info = query_block.get("cost_info", {})
    query_cost = float(cost_info.get("query_cost", 0.0)) if "query_cost" in cost_info else None

    # Extract all table scan nodes
    extracted_tables: list[dict[str, Any]] = []
    _extract_tables_from_json(query_block, extracted_tables)

    total_rows_examined = 0
    indexes_used: list[str] = []
    has_full_table_scan = False
    bottlenecks: list[dict[str, str]] = []
    recommendations: list[dict[str, str]] = []

    # Check for Filesort and Temporary Tables from JSON or Tabular
    using_filesort = _check_flag_in_json(query_block, "using_filesort")
    using_temporary = _check_flag_in_json(query_block, "using_temporary_table")

    for row in tabular_plan:
        extra = str(row.get("Extra") or "")
        if "Using filesort" in extra:
            using_filesort = True
        if "Using temporary" in extra:
            using_temporary = True

    # Inspect each table in the plan
    for tbl in extracted_tables:
        t_name = tbl.get("table_name", "unknown")
        access_type = tbl.get("access_type", "UNKNOWN")
        key_used = tbl.get("key")
        possible_keys = tbl.get("possible_keys", [])
        rows_per_scan = tbl.get("rows_examined_per_scan", 0)
        total_rows_examined += int(rows_per_scan)

        if key_used:
            indexes_used.append(f"{t_name}.{key_used}")

        # Bottleneck: Full Table Scan (access_type == "ALL")
        if access_type == "ALL":
            has_full_table_scan = True
            bottlenecks.append({
                "type": "FULL_TABLE_SCAN",
                "severity": "CRITICAL" if rows_per_scan > 100 else "WARNING",
                "table": t_name,
                "message": f"Full table scan on `{t_name}` (access_type=ALL). MySQL must scan all {rows_per_scan} row(s) because no suitable index was matched."
            })
            if "attached_condition" in tbl:
                cond = tbl["attached_condition"]
                recommendations.append({
                    "category": "INDEXING",
                    "suggestion": f"Create an index on `{t_name}` covering the filter condition `{cond}` to avoid scanning the entire table."
                })
            else:
                recommendations.append({
                    "category": "INDEXING",
                    "suggestion": f"Consider adding an index on `{t_name}` for columns evaluated in the WHERE or JOIN clauses."
                })

        # Bottleneck: Full Index Scan (access_type == "index")
        elif access_type == "index":
            bottlenecks.append({
                "type": "FULL_INDEX_SCAN",
                "severity": "WARNING",
                "table": t_name,
                "message": f"Full index scan on `{t_name}` using index `{key_used}`. The entire index tree is being scanned."
            })

        # Bottleneck: Possible keys exist but none was chosen
        if not key_used and possible_keys:
            bottlenecks.append({
                "type": "INDEX_NOT_USED",
                "severity": "WARNING",
                "table": t_name,
                "message": f"Indexes {possible_keys} exist on `{t_name}`, but the optimizer chose not to use them."
            })
            recommendations.append({
                "category": "OPTIMIZER_HINT",
                "suggestion": f"Check column data types or cardinality on `{t_name}`. An index exists but may be skipped due to type casting or high selectivity estimation."
            })

    # Bottleneck: Filesort
    if using_filesort:
        bottlenecks.append({
            "type": "USING_FILESORT",
            "severity": "WARNING",
            "table": ", ".join(t.get("table_name", "") for t in extracted_tables),
            "message": "Query requires a separate sort pass (Using filesort) to satisfy ORDER BY / GROUP BY clauses."
        })
        recommendations.append({
            "category": "INDEXING",
            "suggestion": "Add an index matching the ORDER BY columns (or a composite index matching WHERE + ORDER BY) to perform index-ordered retrieval and eliminate filesort."
        })

    # Bottleneck: Temporary table
    if using_temporary:
        bottlenecks.append({
            "type": "USING_TEMPORARY",
            "severity": "WARNING",
            "table": ", ".join(t.get("table_name", "") for t in extracted_tables),
            "message": "MySQL created an internal temporary table in memory or on disk to process grouping or sorting."
        })
        recommendations.append({
            "category": "QUERY_STRUCTURE",
            "suggestion": "Align GROUP BY and ORDER BY clauses with the leading columns of an index to avoid creating temporary tables."
        })

    # Check for SELECT * pattern
    if re.search(r"\bSELECT\s+\*", safe_query, re.IGNORECASE):
        bottlenecks.append({
            "type": "WILDCARD_SELECT",
            "severity": "INFO",
            "table": ", ".join(t.get("table_name", "") for t in extracted_tables),
            "message": "Query uses wildcard projection (`SELECT *`), fetching all table columns."
        })
        recommendations.append({
            "category": "PROJECTION",
            "suggestion": "Specify only the columns needed rather than `SELECT *`. This reduces memory overhead, disk I/O, and network bandwidth, and enables index-only (covering index) scans."
        })

    # Positive confirmation if index was utilized and no critical bottlenecks
    if not has_full_table_scan and indexes_used:
        recommendations.append({
            "category": "BEST_PRACTICE",
            "suggestion": f"Good index utilization: queries utilized index(es): {', '.join(set(indexes_used))}."
        })

    # Real-world anti-pattern scan
    anti_patterns = analyze_sql_anti_patterns(safe_query)
    for ap in anti_patterns:
        bottlenecks.append({
            "type": ap["code"],
            "severity": ap["severity"],
            "table": ", ".join(t.get("table_name", "") for t in extracted_tables) or "query",
            "message": f"{ap['name']}: {ap['impact']}",
        })
        recommendations.append({
            "category": "ANTI_PATTERN_FIX",
            "suggestion": ap["remediation"],
        })

    # Overall Performance Rating
    if any(b["severity"] == "CRITICAL" for b in bottlenecks):
        performance_rating = "CRITICAL_BOTTLENECK"
    elif any(b["severity"] == "WARNING" for b in bottlenecks):
        performance_rating = "NEEDS_OPTIMIZATION"
    else:
        performance_rating = "OPTIMIZED"

    return {
        "tabular_plan": tabular_plan,
        "json_plan": json_plan,
        "query_cost": query_cost,
        "total_rows_examined": total_rows_examined,
        "indexes_used": list(set(indexes_used)),
        "has_full_table_scan": has_full_table_scan,
        "using_filesort": using_filesort,
        "using_temporary": using_temporary,
        "bottlenecks": bottlenecks,
        "recommendations": recommendations,
        "anti_patterns": anti_patterns,
        "performance_rating": performance_rating,
    }
