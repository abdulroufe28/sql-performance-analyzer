from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_frontend_index_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "SQL Performance Analyzer" in response.text
    assert "Query Analyzer" in response.text


def test_frontend_css_served():
    response = client.get("/css/styles.css")
    assert response.status_code == 200
    assert "--glass-bg" in response.text or "--bg-dark" in response.text


def test_frontend_js_served():
    response = client.get("/js/app.js")
    assert response.status_code == 200
    assert "runAnalyze" in response.text


def test_frontend_logo_served():
    response = client.get("/assets/logo.svg")
    assert response.status_code == 200
    assert "<svg" in response.text


def test_admin_portal_served():
    response = client.get("/admin.html")
    assert response.status_code == 200
    assert "Superadmin Operations Portal" in response.text


def test_admin_js_served():
    response = client.get("/js/admin.js")
    assert response.status_code == 200
    assert "verifyAdminAccess" in response.text
