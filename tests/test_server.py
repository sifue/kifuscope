from fastapi.testclient import TestClient

from kiou_eval.server import create_app


def test_initial_evaluation_state() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/eval")
    assert response.status_code == 200
    assert response.json()["status"] == "waiting"


def test_overlay_is_served() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/overlay")
    assert response.status_code == 200
    assert "Kifuscope 評価値" in response.text


def test_invalid_sfen_returns_422() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/analyze", json={"sfen": "invalid"})
        state = client.get("/api/eval").json()
    assert response.status_code == 422
    assert state["status"] == "invalid_sfen"


def test_demo_overlay_updates_state() -> None:
    with TestClient(create_app(demo=True)) as client:
        response = client.get("/api/eval")
    assert response.status_code == 200
    assert response.json()["message"] == "デモ評価値"

