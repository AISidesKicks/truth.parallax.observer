"""The watch mode.

Slice 2 of the BDD, the part where the reader only watches.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.demos import DEMOS, get_demo
from src.main import app


@pytest.fixture
def client():
    """A client against the app."""
    with TestClient(app) as test_client:
        yield test_client


def test_the_scripts_are_listed(client: TestClient) -> None:
    """Every script is on offer."""
    response = client.get("/api/demos")

    assert response.status_code == 200
    demos = response.json()
    assert len(demos) == len(DEMOS)
    for demo in demos:
        assert demo["id"]
        assert demo["title"]
        assert demo["lines"]


def test_every_script_exercises_a_path() -> None:
    """Each script asks, pushes back and has a blind spot."""
    for demo in DEMOS:
        assert len(demo.lines) >= 4
        assert any(
            marker in line.text.lower()
            for line in demo.lines
            for marker in ("fair point", "convinced", "that is right", "i agree")
        )
        assert any(line.note for line in demo.lines)


def test_a_script_can_be_started(client: TestClient) -> None:
    """Starting one gives a session and the script."""
    response = client.post("/api/demo", json={"id": "flat-earth-horizon"})

    assert response.status_code == 200
    data = response.json()
    assert data["session"]["belief"] == "the Earth is flat"
    assert data["session"]["worldview"] == "spherical-earth"
    assert data["demo"]["id"] == "flat-earth-horizon"


def test_an_unknown_script_is_a_404(client: TestClient) -> None:
    """A script that does not exist."""
    response = client.post("/api/demo", json={"id": "nope"})

    assert response.status_code == 404


def test_the_script_plays_out(client: TestClient) -> None:
    """The visitor's side is scripted, the agent answers live."""
    demo = get_demo("flat-earth-horizon")
    assert demo is not None

    started = client.post("/api/demo", json={"id": demo.id}).json()
    session_id = started["session"]["id"]

    with client.websocket_connect(
        f"/ws/demo/{session_id}?demo={demo.id}"
    ) as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "ready"
        assert ready["demo"]["id"] == demo.id

        seen: list[str] = []
        replies = 0
        typed = ""

        for _ in range(400):
            message = websocket.receive_json()
            kind = message["type"]

            if kind == "typing":
                typed += message["text"]
            elif kind == "line":
                assert typed == message["text"]
                seen.append(message["text"])
                typed = ""
            elif kind == "reply":
                replies += 1
                assert message["turn"]["reply"]
            elif kind == "done":
                assert message["summary"]["turns"] == len(demo.lines)
                break
            elif kind == "error":
                raise AssertionError(message["message"])

    assert seen == [line.text for line in demo.lines]
    assert replies == len(demo.lines)


def test_the_reader_can_take_over(client: TestClient) -> None:
    """A message from the reader stops the script."""
    demo = get_demo("flat-earth-horizon")
    assert demo is not None

    started = client.post("/api/demo", json={"id": demo.id}).json()
    session_id = started["session"]["id"]

    with client.websocket_connect(
        f"/ws/demo/{session_id}?demo={demo.id}"
    ) as websocket:
        websocket.receive_json()

        # let the first line play, then cut in
        for _ in range(400):
            message = websocket.receive_json()
            if message["type"] == "line":
                break

        websocket.send_json({"type": "message", "text": "wait, hold on"})

        taken_over = False
        for _ in range(400):
            message = websocket.receive_json()
            if message["type"] == "line" and message.get("taken_over"):
                taken_over = True
                break

    assert taken_over
