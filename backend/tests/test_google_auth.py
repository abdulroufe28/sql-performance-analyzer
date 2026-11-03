from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.core.database import AppSessionLocal
from backend.app.main import app
from backend.app.models.user import User


client = TestClient(app)


def test_google_config_endpoint():
    res = client.get("/api/v1/auth/google/config")
    assert res.status_code == 200
    assert "enabled" in res.json()


def test_login_with_google_success_creates_user():
    test_google_email = "new_google_dev@gmail.com"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "email": test_google_email,
        "email_verified": "true",
        "name": "Google Developer",
        "sub": "1234567890",
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        res = client.post(
            "/api/v1/auth/google",
            json={"credential": "mock_valid_google_jwt_token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data

    # Verify user exists in database
    db = AppSessionLocal()
    user = db.query(User).filter(User.email == test_google_email).first()
    assert user is not None
    assert user.full_name == "Google Developer"

    # Cleanup
    db.execute(delete(User).where(User.email == test_google_email))
    db.commit()
    db.close()


def test_login_with_google_invalid_token():
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error_description": "Invalid Value"}

    with patch("httpx.Client.get", return_value=mock_resp):
        res = client.post(
            "/api/v1/auth/google",
            json={"credential": "invalid_fake_token"},
        )
        assert res.status_code == 401
        assert "invalid or expired" in res.json()["detail"].lower()


def test_login_with_google_dev_simulator():
    dev_email = "abdul_test_dev@gmail.com"
    res = client.post(
        "/api/v1/auth/google",
        json={"credential": f"dev_google_:{dev_email}:Abdul Roufe"},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()

    # Cleanup
    db = AppSessionLocal()
    db.execute(delete(User).where(User.email == dev_email))
    db.commit()
    db.close()

