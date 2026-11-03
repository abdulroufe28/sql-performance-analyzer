import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.core.database import AppSessionLocal
from backend.app.core.security import create_access_token, hash_password
from backend.app.main import app
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.query_comparison import QueryComparison
from backend.app.models.user import User


client = TestClient(app)


@pytest.fixture
def auth_users():
    db = AppSessionLocal()
    regular_email = f"regular_{uuid.uuid4().hex[:8]}@example.com"
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"

    regular_user = User(
        email=regular_email,
        password_hash=hash_password("Pass123!"),
        full_name="Regular User",
        is_active=True,
        role="USER",
    )
    admin_user = User(
        email=admin_email,
        password_hash=hash_password("AdminPass123!"),
        full_name="Admin User",
        is_active=True,
        role="ADMIN",
    )

    db.add_all([regular_user, admin_user])
    db.commit()
    db.refresh(regular_user)
    db.refresh(admin_user)

    reg_token = create_access_token(str(regular_user.id))
    admin_token = create_access_token(str(admin_user.id))

    yield {
        "regular_user": regular_user,
        "admin_user": admin_user,
        "reg_token": reg_token,
        "admin_token": admin_token,
    }

    # Teardown
    db.execute(delete(QueryAnalysis).where(QueryAnalysis.user_id.in_([regular_user.id, admin_user.id])))
    db.execute(delete(QueryComparison).where(QueryComparison.user_id.in_([regular_user.id, admin_user.id])))
    db.execute(delete(User).where(User.id.in_([regular_user.id, admin_user.id])))
    db.commit()
    db.close()


def test_user_dashboard_metrics(auth_users):
    headers = {"Authorization": f"Bearer {auth_users['reg_token']}"}

    # Analyze a query first
    client.post("/api/v1/queries/analyze", json={"query": "SELECT * FROM customers;"}, headers=headers)

    res = client.get("/api/v1/dashboard/metrics", headers=headers)
    assert res.status_code == 200

    data = res.json()
    assert data["total_queries"] >= 1
    assert data["avg_execution_time_ms"] >= 0
    assert "comparison_quota_limit" in data
    assert len(data["recent_queries"]) >= 1


def test_admin_dashboard_forbidden_for_regular_user(auth_users):
    headers = {"Authorization": f"Bearer {auth_users['reg_token']}"}

    res = client.get("/api/v1/admin/dashboard", headers=headers)
    assert res.status_code == 403
    assert "admin" in res.json()["detail"].lower()


def test_admin_dashboard_allowed_for_admin_user(auth_users):
    headers = {"Authorization": f"Bearer {auth_users['admin_token']}"}

    res = client.get("/api/v1/admin/dashboard", headers=headers)
    assert res.status_code == 200

    data = res.json()
    assert data["user_stats"]["total_users"] >= 2
    assert data["user_stats"]["admin_users"] >= 1
    assert data["health"]["app_database"] == "ONLINE"
    assert data["health"]["analysis_database"] == "ONLINE"
    assert data["health"]["status"] == "HEALTHY"
