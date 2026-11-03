import re
from typing import Any


def analyze_sql_anti_patterns(query: str) -> list[dict[str, str]]:
    """
    Scans SQL queries for production database anti-patterns that degrade
    latency, bypass B-Tree indexes, or consume excessive I/O and buffer pool memory.
    """
    detected: list[dict[str, str]] = []
    clean_sql = re.sub(r"\s+", " ", query).strip()

    # 1. Leading Wildcard in LIKE predicate
    if re.search(r"\bLIKE\s+['\"][%_]", clean_sql, re.IGNORECASE):
        detected.append({
            "code": "LEADING_WILDCARD_LIKE",
            "severity": "CRITICAL",
            "name": "Leading Wildcard in LIKE Predicate",
            "impact": "Using LIKE '%pattern' prevents B-Tree index lookup and forces a full table scan on every row.",
            "remediation": "Use prefix matching (e.g. 'term%'), MySQL FULLTEXT index (MATCH ... AGAINST), or an external search index.",
        })

    # 2. Function calls on predicate columns (Non-Sargable Query)
    func_match = re.search(r"\bWHERE\b.*?\b(YEAR|MONTH|DAY|DATE|LOWER|UPPER|SUBSTRING|TRIM)\s*\((\w+)\)", clean_sql, re.IGNORECASE)
    if func_match:
        func_name = func_match.group(1).upper()
        col_name = func_match.group(2)
        detected.append({
            "code": "NON_SARGABLE_FUNCTION_CALL",
            "severity": "CRITICAL",
            "name": f"Non-Sargable Function ({func_name}) on Filter Column",
            "impact": f"Applying `{func_name}({col_name})` in the WHERE clause invalidates any B-Tree index on `{col_name}` because MySQL must compute the function per row.",
            "remediation": f"Rewrite the predicate to compare the raw column against a range (e.g. `{col_name} >= '2026-01-01' AND {col_name} < '2027-01-01'`).",
        })

    # 3. SELECT * Wildcard in Production
    if re.search(r"\bSELECT\s+\*\b", clean_sql, re.IGNORECASE):
        detected.append({
            "code": "WILDCARD_PROJECTION",
            "severity": "WARNING",
            "name": "Wildcard Column Projection (`SELECT *`)",
            "impact": "Fetches all columns including unused text/blob data, increasing network transfer, disk I/O, and preventing covering index (index-only) execution.",
            "remediation": "Explicitly select only the necessary columns (e.g. `SELECT id, name FROM ...`).",
        })

    # 4. Unbounded Query (Missing WHERE or LIMIT)
    if not re.search(r"\bWHERE\b", clean_sql, re.IGNORECASE) and not re.search(r"\bLIMIT\b", clean_sql, re.IGNORECASE):
        detected.append({
            "code": "UNBOUNDED_SCAN",
            "severity": "WARNING",
            "name": "Unbounded Table Scan",
            "impact": "Query contains neither a WHERE clause nor a LIMIT clause, risking exhaustion of MySQL buffer pool on large tables.",
            "remediation": "Add a selective WHERE predicate or a restrictive LIMIT clause.",
        })

    # 5. Deep Offset Pagination Penalty
    offset_match = re.search(r"\bOFFSET\s+(\d+)\b", clean_sql, re.IGNORECASE) or re.search(r"\bLIMIT\s+(\d+)\s*,\s*\d+\b", clean_sql, re.IGNORECASE)
    if offset_match:
        offset_val = int(offset_match.group(1))
        if offset_val > 1000:
            detected.append({
                "code": "DEEP_OFFSET_PENALTY",
                "severity": "WARNING",
                "name": "Deep Offset Pagination Penalty",
                "impact": f"OFFSET {offset_val} forces the database to read and discard {offset_val} rows before returning results.",
                "remediation": "Switch to cursor-based / keyset pagination (e.g. `WHERE id > :last_seen_id ORDER BY id LIMIT 20`).",
            })

    return detected
