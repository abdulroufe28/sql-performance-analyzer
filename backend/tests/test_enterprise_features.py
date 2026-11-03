import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.core.database import AppSessionLocal
from backend.app.core.security import create_access_token, hash_password
from backend.app.main import app
from backend.app.models.feedback import UserFeedback
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.security_audit import SecurityAuditLog
from backend.app.models.user import User


client = TestClient(app)


@pytest.fixture
def enterprise_users():
    db = AppSessionLocal()
    u_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    a_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"

    user = User(
        email=u_email,
        password_hash=hash_password("Pass123!"),
        full_name="Enterprise User",
        is_active=True,
        role="USER",
    )
    admin = User(
        email=a_email,
        password_hash=hash_password("AdminPass123!"),
        full_name="Enterprise Admin",
        is_active=True,
        role="ADMIN",
    )
    db.add_all([user, admin])
    db.commit()
    db.refresh(user)
    db.refresh(admin)

    u_token = create_access_token(str(user.id))
    a_token = create_access_token(str(admin.id))

    yield {
        "user": user,
        "admin": admin,
        "u_token": u_token,
        "a_token": a_token,
    }

    # Teardown
    db.execute(delete(UserFeedback).where(UserFeedback.user_id.in_([user.id, admin.id])))
    db.execute(delete(SecurityAuditLog).where(SecurityAuditLog.user_id.in_([user.id, admin.id])))
    db.execute(delete(QueryAnalysis).where(QueryAnalysis.user_id.in_([user.id, admin.id])))
    db.execute(delete(User).where(User.id.in_([user.id, admin.id])))
    db.commit()
    db.close()


def test_submit_and_get_user_feedback(enterprise_users):
    headers = {"Authorization": f"Bearer {enterprise_users['u_token']}"}
    payload = {
        "category": "FEATURE_REQUEST",
        "rating": 5,
        "comment": "Adding visual flame graphs for query stages would be awesome!",
    }

    create_res = client.post("/api/v1/feedback", json=payload, headers=headers)
    assert create_res.status_code == 201
    fb_data = create_res.json()
    assert fb_data["category"] == "FEATURE_REQUEST"
    assert fb_data["rating"] == 5
    assert fb_data["status"] == "PENDING"

    # User retrieves their feedback
    my_res = client.get("/api/v1/feedback/my", headers=headers)
    assert my_res.status_code == 200
    items = my_res.json()
    assert len(items) >= 1
    assert items[0]["comment"] == payload["comment"]


def test_security_audit_logging_on_blocked_query(enterprise_users):
    headers = {"Authorization": f"Bearer {enterprise_users['u_token']}"}

    # Attempt a blocked destructive SQL query
    bad_query = "DROP TABLE customers;"
    res = client.post("/api/v1/queries/analyze", json={"query": bad_query}, headers=headers)
    assert res.status_code == 400

    # Admin checks security audit logs
    admin_headers = {"Authorization": f"Bearer {enterprise_users['a_token']}"}
    logs_res = client.get("/api/v1/admin/security-logs", headers=admin_headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    assert any("DROP TABLE" in l["attempted_query"] for l in logs)


def test_admin_telemetry_and_user_management(enterprise_users):
    admin_headers = {"Authorization": f"Bearer {enterprise_users['a_token']}"}

    # 1. Server Hardware Telemetry in Admin Dashboard
    dash_res = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    telemetry = dash_data["telemetry"]
    assert "cpu_percent" in telemetry
    assert telemetry["memory_total_gb"] > 0
    assert telemetry["disk_total_gb"] > 0

    # 2. List all users
    users_res = client.get("/api/v1/admin/users", headers=admin_headers)
    assert users_res.status_code == 200
    users_list = users_res.json()
    assert len(users_list) >= 2

    # 3. Toggle user active status
    target_user_id = enterprise_users["user"].id
    status_res = client.patch(
        f"/api/v1/admin/users/{target_user_id}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert status_res.status_code == 200


def test_export_query_analysis_report(enterprise_users):
    headers = {"Authorization": f"Bearer {enterprise_users['u_token']}"}

    # Run query first
    analyze_res = client.post(
        "/api/v1/queries/analyze",
        json={"query": "SELECT * FROM customers WHERE id = 1;"},
        headers=headers,
    )
    assert analyze_res.status_code == 200

    # Get history to find ID
    hist_res = client.get("/api/v1/queries/history", headers=headers)
    analysis_id = hist_res.json()["items"][0]["id"]

    # Export report
    export_res = client.get(f"/api/v1/queries/analyses/{analysis_id}/export", headers=headers)
    assert export_res.status_code == 200
    report = export_res.json()
    assert report["report_type"] == "Database Performance Analysis Report"
    assert report["analysis_id"] == analysis_id
    assert "exported_by" in report
