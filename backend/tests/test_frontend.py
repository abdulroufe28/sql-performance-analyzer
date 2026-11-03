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
    assert "--bg-primary" in response.text


def test_frontend_js_served():
    response = client.get("/js/app.js")
    assert response.status_code == 200
    assert "runAnalyze" in response.text
