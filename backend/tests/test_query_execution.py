import pytest

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import AppSessionLocal
from backend.app.core.security import create_access_token, hash_password
from backend.app.main import app
from backend.app.models.user import User
from backend.app.services.query_execution_service import (
    execute_read_only_query,
)
from backend.app.services.sql_safety_service import SQLSafetyError


client = TestClient(app)


def test_get_analysis_schema():
    db = AppSessionLocal()
    email = f"schema_user_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        password_hash=hash_password("Pass123!"),
        full_name="Schema User",
        is_active=True,
        role="USER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/queries/schema", headers=headers)
    assert res.status_code == 200
    tables = res.json()["tables"]
    table_names = [t["name"] for t in tables]
    assert "customers" in table_names
    assert "orders" in table_names

    db.delete(user)
    db.commit()
    db.close()



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