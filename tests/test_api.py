"""The HTTP surface.

These run against the app with the real lifespan, so the model server and
the memory server are both absent. The app has to come up anyway.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """A client against the app, with the lifespan running."""
    with TestClient(app) as test_client:
        yield test_client


def test_the_app_is_up(client: TestClient) -> None:
    """Health."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_the_interface_is_served(client: TestClient) -> None:
    """The page loads."""
    response = client.get("/")

    assert response.status_code == 200
    assert "parallax.observer" in response.text


def test_the_status_works_without_a_model_server(client: TestClient) -> None:
    """The bar shows the app is fine, the model is not."""
    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()
    assert "llm" in data
    assert "viking" in data


def test_a_session_can_be_created(client: TestClient) -> None:
    """Start a session."""
    response = client.post(
        "/api/session",
        json={"alterego": "Sam", "belief": "the Earth is flat"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["alterego"] == "Sam"
    assert data["goal"] == "spherical-earth"
    assert data["id"]


def test_a_session_can_be_read_back(client: TestClient) -> None:
    """The transcript survives."""
    created = client.post(
        "/api/session", json={"alterego": "Sam", "belief": "the Earth is flat"}
    ).json()

    response = client.get(f"/api/session/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_a_missing_session_is_a_404(client: TestClient) -> None:
    """Asking for a session that is not there."""
    response = client.get("/api/session/nope")

    assert response.status_code == 404


def test_the_sessions_can_be_listed(client: TestClient) -> None:
    """Every session."""
    client.post("/api/session", json={"alterego": "Sam"})

    response = client.get("/api/sessions")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_the_websocket_closes_on_an_unknown_session(client: TestClient) -> None:
    """No crash on a bad session."""
    from starlette.websockets import WebSocketDisconnect

    with client.websocket_connect("/ws/nope") as websocket:
        message = websocket.receive_json()
        assert message["type"] == "error"

        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()
