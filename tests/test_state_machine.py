import uuid

import pytest

from app.domain.state_machine import InvalidTransitionError, StateMachine


class _FakeObj:
    """A minimal stand-in with just what StateMachine.transition needs (an id and a state) --
    proves the engine is generic and doesn't secretly depend on Project."""

    def __init__(self, state):
        self.id = uuid.uuid4()
        self.state = state


def test_valid_transition_updates_state_and_records_event(session):
    machine = StateMachine({"OPEN": {"CLOSED"}})
    obj = _FakeObj("OPEN")

    machine.transition(session, obj, "fake_entity", "CLOSED")
    session.commit()

    assert obj.state == "CLOSED"

    from sqlalchemy import select

    from app.core.models.event import Event

    events = session.execute(
        select(Event).where(Event.entity_type == "fake_entity", Event.entity_id == obj.id)
    ).scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "state_transition"
    assert events[0].payload == {"from": "OPEN", "to": "CLOSED"}


def test_invalid_transition_raises_and_does_not_mutate_state(session):
    machine = StateMachine({"OPEN": {"CLOSED"}})
    obj = _FakeObj("OPEN")

    with pytest.raises(InvalidTransitionError):
        machine.transition(session, obj, "fake_entity", "ARCHIVED")

    assert obj.state == "OPEN"


def test_can_transition_is_a_pure_check_with_no_side_effects(session):
    machine = StateMachine({"OPEN": {"CLOSED"}})
    assert machine.can_transition("OPEN", "CLOSED") is True
    assert machine.can_transition("OPEN", "ARCHIVED") is False
    assert machine.can_transition("CLOSED", "OPEN") is False  # no transition defined backwards
