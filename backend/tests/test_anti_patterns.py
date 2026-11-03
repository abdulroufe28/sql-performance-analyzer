from backend.app.services.anti_pattern_service import analyze_sql_anti_patterns


def test_anti_pattern_leading_wildcard_like():
    sql = "SELECT id, name FROM customers WHERE email LIKE '%gmail.com';"
    patterns = analyze_sql_anti_patterns(sql)
    codes = [p["code"] for p in patterns]
    assert "LEADING_WILDCARD_LIKE" in codes
    assert any(p["severity"] == "CRITICAL" for p in patterns)


def test_anti_pattern_non_sargable_function_call():
    sql = "SELECT id, total_amount FROM orders WHERE YEAR(order_date) = 2026;"
    patterns = analyze_sql_anti_patterns(sql)
    codes = [p["code"] for p in patterns]
    assert "NON_SARGABLE_FUNCTION_CALL" in codes
    assert any("YEAR" in p["name"] for p in patterns)


def test_anti_pattern_unbounded_scan():
    sql = "SELECT id, name FROM customers;"
    patterns = analyze_sql_anti_patterns(sql)
    codes = [p["code"] for p in patterns]
    assert "UNBOUNDED_SCAN" in codes


def test_anti_pattern_deep_offset_penalty():
    sql = "SELECT id, name FROM customers WHERE id > 0 LIMIT 10 OFFSET 5000;"
    patterns = analyze_sql_anti_patterns(sql)
    codes = [p["code"] for p in patterns]
    assert "DEEP_OFFSET_PENALTY" in codes
