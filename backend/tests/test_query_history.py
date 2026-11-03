import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.core.database import AppSessionLocal
from backend.app.core.security import create_access_token, hash_password
from backend.app.main import app
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.user import User


client = TestClient(app)


@pytest.fixture
def setup_history_data():
    db = AppSessionLocal()
    user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@example.com"
    user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@example.com"

    user_a = User(
        email=user_a_email,
        password_hash=hash_password("Password123!"),
        full_name="User A",
        is_active=True,
        role="USER",
    )
    user_b = User(
        email=user_b_email,
        password_hash=hash_password("Password123!"),
        full_name="User B",
        is_active=True,
        role="USER",
    )
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    now = datetime.now(timezone.utc)
    analyses_a = [
        QueryAnalysis(
            user_id=user_a.id,
            query="SELECT * FROM customers WHERE id = 1;",
            execution_time_ms=1.1,
            row_count=1,
            created_at=now - timedelta(minutes=10),
        ),
        QueryAnalysis(
            user_id=user_a.id,
            query="SELECT * FROM customers WHERE id = 2;",
            execution_time_ms=2.2,
            row_count=1,
            created_at=now - timedelta(minutes=5),
        ),
        QueryAnalysis(
            user_id=user_a.id,
            query="SELECT * FROM customers WHERE id = 3;",
            execution_time_ms=3.3,
            row_count=1,
            created_at=now,
        ),
    ]

    analysis_b = QueryAnalysis(
        user_id=user_b.id,
        query="SELECT * FROM orders;",
        execution_time_ms=4.4,
        row_count=6,
        created_at=now,
    )

    db.add_all(analyses_a + [analysis_b])
    db.commit()

    token_a = create_access_token(str(user_a.id))
    token_b = create_access_token(str(user_b.id))

    yield {
        "user_a": user_a,
        "user_b": user_b,
        "token_a": token_a,
        "token_b": token_b,
    }

    # Clean up test artifacts
    db.execute(delete(QueryAnalysis).where(QueryAnalysis.user_id.in_([user_a.id, user_b.id])))
    db.execute(delete(User).where(User.id.in_([user_a.id, user_b.id])))
    db.commit()
    db.close()


def test_get_history_unauthenticated():
    response = client.get("/api/v1/queries/history")
    assert response.status_code in (401, 403)


def test_get_history_user_isolation(setup_history_data):
    data = setup_history_data
    headers_a = {"Authorization": f"Bearer {data['token_a']}"}
    headers_b = {"Authorization": f"Bearer {data['token_b']}"}

    # User A query
    res_a = client.get("/api/v1/queries/history", headers=headers_a)
    assert res_a.status_code == 200
    json_a = res_a.json()
    assert json_a["total"] == 3
    assert len(json_a["items"]) == 3
    # Check that User B's query is never in User A's history
    queries_a = [item["query"] for item in json_a["items"]]
    assert "SELECT * FROM orders;" not in queries_a

    # User B query
    res_b = client.get("/api/v1/queries/history", headers=headers_b)
    assert res_b.status_code == 200
    json_b = res_b.json()
    assert json_b["total"] == 1
    assert len(json_b["items"]) == 1
    assert json_b["items"][0]["query"] == "SELECT * FROM orders;"


def test_get_history_pagination(setup_history_data):
    data = setup_history_data
    headers = {"Authorization": f"Bearer {data['token_a']}"}

    # Page 1 with page_size=2
    res_p1 = client.get("/api/v1/queries/history?page=1&page_size=2", headers=headers)
    assert res_p1.status_code == 200
    body_p1 = res_p1.json()
    assert body_p1["page"] == 1
    assert body_p1["page_size"] == 2
    assert body_p1["total"] == 3
    assert body_p1["total_pages"] == 2
    assert len(body_p1["items"]) == 2

    # Page 2 with page_size=2
    res_p2 = client.get("/api/v1/queries/history?page=2&page_size=2", headers=headers)
    assert res_p2.status_code == 200
    body_p2 = res_p2.json()
    assert body_p2["page"] == 2
    assert body_p2["page_size"] == 2
    assert body_p2["total"] == 3
    assert body_p2["total_pages"] == 2
    assert len(body_p2["items"]) == 1


def test_get_history_ordering_newest_first(setup_history_data):
    data = setup_history_data
    headers = {"Authorization": f"Bearer {data['token_a']}"}

    res = client.get("/api/v1/queries/history?page=1&page_size=10", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]

    # Items should be ordered from newest to oldest
    assert items[0]["query"] == "SELECT * FROM customers WHERE id = 3;"
    assert items[1]["query"] == "SELECT * FROM customers WHERE id = 2;"
    assert items[2]["query"] == "SELECT * FROM customers WHERE id = 1;"


def test_get_history_invalid_pagination_parameters(setup_history_data):
    data = setup_history_data
    headers = {"Authorization": f"Bearer {data['token_a']}"}

    # page < 1
    res_page_zero = client.get("/api/v1/queries/history?page=0", headers=headers)
    assert res_page_zero.status_code == 422

    # page_size > 100
    res_page_size_too_large = client.get("/api/v1/queries/history?page_size=101", headers=headers)
    assert res_page_size_too_large.status_code == 422
