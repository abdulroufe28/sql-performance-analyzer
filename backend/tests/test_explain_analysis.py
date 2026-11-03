from backend.app.services.explain_service import get_explain_plan


def test_explain_plan_full_table_scan():
    # Query without index filter on customers table
    plan = get_explain_plan("SELECT * FROM customers WHERE email = 'arun@example.com'")

    assert plan["has_full_table_scan"] is True
    assert plan["performance_rating"] in ("NEEDS_OPTIMIZATION", "CRITICAL_BOTTLENECK")
    assert any(b["type"] == "FULL_TABLE_SCAN" for b in plan["bottlenecks"])
    assert any(r["category"] == "INDEXING" for r in plan["recommendations"])
    assert len(plan["tabular_plan"]) >= 1
    assert "query_block" in plan["json_plan"]


def test_explain_plan_primary_key_lookup():
    # Query with PRIMARY key index lookup
    plan = get_explain_plan("SELECT id, name FROM customers WHERE id = 1")

    assert plan["has_full_table_scan"] is False
    assert plan["performance_rating"] == "OPTIMIZED"
    assert "customers.PRIMARY" in plan["indexes_used"]
    assert not any(b["type"] == "FULL_TABLE_SCAN" for b in plan["bottlenecks"])


def test_explain_plan_filesort_detection():
    # ORDER BY unindexed column triggers filesort
    plan = get_explain_plan("SELECT * FROM customers ORDER BY city")

    assert plan["using_filesort"] is True
    assert any(b["type"] == "USING_FILESORT" for b in plan["bottlenecks"])


def test_explain_plan_wildcard_select_detection():
    # SELECT * is detected and advised against
    plan = get_explain_plan("SELECT * FROM customers WHERE id = 1")

    assert any(b["type"] == "WILDCARD_SELECT" for b in plan["bottlenecks"])
    assert any(r["category"] == "PROJECTION" for r in plan["recommendations"])
