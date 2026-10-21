"""The session scenarios.

Slice 1, feature: A session.
"""

from __future__ import annotations

from src.session import SessionStore


def test_a_visitor_picks_a_name_and_a_belief(store: SessionStore) -> None:
    """The session knows the belief it has to argue against."""
    session = store.create(alterego="Sam", belief="the Earth is flat")

    assert session.alterego == "Sam"
    assert session.belief == "the Earth is flat"
    assert session.worldview == "spherical-earth"
    assert session.goal == "spherical-earth"


def test_a_visitor_who_does_not_say_what_they_believe(store: SessionStore) -> None:
    """No belief means the most common position."""
    session = store.create(alterego="Sam")

    assert session.belief == "the Earth is round"
    assert session.worldview == "flat-earth"
    assert session.goal == "flat-earth"


def test_the_goal_can_be_set_explicitly(store: SessionStore) -> None:
    """The goal is the visitor's choice too."""
    session = store.create(
        alterego="Sam",
        belief="the Earth is flat",
        goal="the Earth is a disc",
    )

    assert session.goal == "the Earth is a disc"


def test_two_visitors_with_the_same_name_get_different_sessions(
    store: SessionStore,
) -> None:
    """The same name does not collide."""
    first = store.create(alterego="Sam", belief="the Earth is flat")
    second = store.create(alterego="Sam", belief="the Earth is round")

    assert first.id != second.id
    assert store.get(first.id).belief == "the Earth is flat"
    assert store.get(second.id).belief == "the Earth is round"


def test_the_profile_is_written_to_disk(store: SessionStore, tmp_path) -> None:
    """The session survives a restart."""
    session = store.create(alterego="Sam", belief="the Earth is flat")

    profile = tmp_path / session.id / "profile"
    assert (profile / "target-belief.md").read_text() == "the Earth is flat"
    assert (profile / "persuasion-goal.md").read_text() == "spherical-earth"
    assert (profile / "alterego-name.md").read_text() == "Sam"


def test_a_missing_session_is_none(store: SessionStore) -> None:
    """Asking for a session that is not there gives none."""
    assert store.get("nope") is None
