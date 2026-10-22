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


def test_the_models_can_be_listed(client: TestClient) -> None:
    """The catalogue the picker is filled from."""
    response = client.get("/api/models")

    assert response.status_code == 200
    data = response.json()
    assert data["default"]
    assert data["models"]
    assert all(entry["id"] for entry in data["models"])


def test_a_session_keeps_the_model_it_was_asked_for(client: TestClient) -> None:
    """The visitor picks the model."""
    response = client.post(
        "/api/session",
        json={"alterego": "Sam", "belief": "the Earth is flat", "model": "granite-4.0-h-tiny"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "granite-4.0-h-tiny"


def test_a_session_with_an_unknown_model_gets_the_default(client: TestClient) -> None:
    """A model the catalogue does not know is refused."""
    from src.config import default_model

    response = client.post(
        "/api/session",
        json={"alterego": "Sam", "model": "a-model-that-does-not-exist"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == default_model()


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


async def test_a_fire_chat_debate_runs(client: TestClient, monkeypatch) -> None:
    """Three sides, the stages, and a verdict."""
    import json as json_module

    from src.main import app
    from tests.test_fire_chat import TypedLLM, WorldviewViking

    # the real model server takes a minute for a whole debate, and the
    # point of this test is the wiring, not the model
    monkeypatch.setattr(app.state.models, "get", lambda model="": TypedLLM())
    monkeypatch.setattr(app.state, "viking", WorldviewViking(), raising=False)

    created = client.post(
        "/api/session", json={"alterego": "Sam", "belief": "the Earth is flat"}
    ).json()

    with client.websocket_connect(f"/ws/fire/{created['id']}") as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "ready"

        websocket.send_json({"type": "start", "topic": "the shape of the Earth"})

        speeches = []
        stages = []
        while True:
            message = websocket.receive_json()
            if message["type"] == "speech":
                speeches.append(message["speech"])
            elif message["type"] == "stage":
                stages.append(message["stage"])
            elif message["type"] == "verdict":
                verdict = message["moderation"]
                break
            elif message["type"] == "error":
                raise AssertionError(message["message"])

    assert len(speeches) == 12
    assert stages[:3] == ["opening"] * 3
    assert "winner" in verdict
    assert json_module.dumps(verdict)
