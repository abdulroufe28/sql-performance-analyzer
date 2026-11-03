import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.core.database import AppSessionLocal
from backend.app.core.security import create_access_token, hash_password
from backend.app.main import app
from backend.app.models.query_comparison import QueryComparison
from backend.app.models.user import User


client = TestClient(app)


@pytest.fixture
def test_user():
    db = AppSessionLocal()
    email = f"compare_user_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        password_hash=hash_password("Secret123!"),
        full_name="Compare User",
        is_active=True,
        role="USER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))

    yield {
        "user": user,
        "token": token,
    }

    # Cleanup
    db.execute(delete(QueryComparison).where(QueryComparison.user_id == user.id))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    db.close()


def test_compare_queries_success(test_user):
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    payload = {
        "title": "Index vs Full Scan",
        "query_a": "SELECT id, name FROM customers WHERE id = 1;",
        "query_b": "SELECT * FROM customers WHERE email = 'arun@example.com';",
    }

    response = client.post("/api/v1/queries/compare", json=payload, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Index vs Full Scan"
    assert "query_a" in data
    assert "query_b" in data
    assert data["faster_query"] in ("QUERY_A", "QUERY_B", "TIE")
    assert "verdict" in data
    assert data["time_diff_ms"] >= 0


def test_compare_queries_persisted_and_retrieved(test_user):
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    payload = {
        "title": "Saved Comparison Test",
        "query_a": "SELECT * FROM customers WHERE id = 2;",
        "query_b": "SELECT * FROM customers WHERE id = 3;",
    }

    create_res = client.post("/api/v1/queries/compare", json=payload, headers=headers)
    assert create_res.status_code == 200

    # Retrieve comparisons history
    history_res = client.get("/api/v1/queries/comparisons", headers=headers)
    assert history_res.status_code == 200

    history_data = history_res.json()
    assert history_data["total"] >= 1
    assert history_data["items"][0]["title"] == "Saved Comparison Test"


def test_compare_queries_quota_limit(test_user):
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    db = AppSessionLocal()

    # Pre-seed 10 comparisons directly into database for this user
    for i in range(10):
        c = QueryComparison(
            user_id=test_user["user"].id,
            title=f"Comparison {i}",
            query_a="SELECT * FROM customers WHERE id = 1;",
            query_b="SELECT * FROM customers WHERE id = 2;",
            query_a_time_ms=1.0,
            query_b_time_ms=1.2,
            faster_query="QUERY_A",
            speedup_percentage=16.6,
        )
        db.add(c)
    db.commit()
    db.close()

    # The 11th comparison must be rejected with 403 Forbidden
    payload = {
        "title": "Over Quota",
        "query_a": "SELECT * FROM customers WHERE id = 1;",
        "query_b": "SELECT * FROM customers WHERE id = 2;",
    }
    over_limit_res = client.post("/api/v1/queries/compare", json=payload, headers=headers)
    assert over_limit_res.status_code == 403
    assert "quota" in over_limit_res.json()["detail"].lower()
