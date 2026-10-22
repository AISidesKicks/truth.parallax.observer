"""The model layer.

The visitor picks the model, the session keeps it, and the app talks to the
right one.
"""

from __future__ import annotations

from pathlib import Path

from src.config import catalogue_models, chat_models, default_model, read_catalogue
from src.main import pick_model
from src.session import SessionStore


def test_the_catalogue_lists_the_models() -> None:
    """Every model the router serves is in the catalogue."""
    entries = catalogue_models()

    assert entries
    assert all(entry.id for entry in entries)
    assert all(entry.role in {"chat", "embedding"} for entry in entries)


def test_the_chat_models_are_the_ones_the_visitor_picks() -> None:
    """The encoder is not a choice."""
    chat = chat_models()
    embedding = [entry for entry in catalogue_models() if entry.role == "embedding"]

    assert chat
    assert embedding
    assert not {entry.id for entry in chat} & {entry.id for entry in embedding}


def test_the_default_model_is_a_chat_model() -> None:
    """The default has to be one the visitor could have picked."""
    assert default_model() in {entry.id for entry in chat_models()}


def test_a_missing_catalogue_is_not_a_crash(tmp_path: Path) -> None:
    """No catalogue, no models, no error."""
    empty = tmp_path / "models.toml"

    assert catalogue_models(empty) == []
    assert chat_models(empty) == []
    assert read_catalogue(empty) == {}


def test_a_broken_catalogue_is_not_a_crash(tmp_path: Path) -> None:
    """A broken file does not take the app down."""
    broken = tmp_path / "models.toml"
    broken.write_text("this is not toml = = =\n")

    assert catalogue_models(broken) == []


def test_a_session_keeps_the_model_it_was_given(store: SessionStore) -> None:
    """The model is part of the session."""
    session = store.create(alterego="Sam", model="granite-4.0-h-tiny")

    assert session.model == "granite-4.0-h-tiny"
    assert session.to_dict()["model"] == "granite-4.0-h-tiny"


def test_a_session_without_a_model_has_none(store: SessionStore) -> None:
    """No choice, no model."""
    session = store.create(alterego="Sam")

    assert session.model == ""


def test_a_known_model_is_kept() -> None:
    """A model from the catalogue is taken."""
    known = chat_models()[0].id

    assert pick_model(known) == known


def test_an_unknown_model_falls_back_to_the_default() -> None:
    """A model the catalogue does not know is refused."""
    assert pick_model("a-model-that-does-not-exist") == default_model()


def test_no_model_falls_back_to_the_default() -> None:
    """The visitor picked nothing."""
    assert pick_model("") == default_model()
