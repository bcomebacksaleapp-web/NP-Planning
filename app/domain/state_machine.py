from app.domain.events import record_event


class InvalidTransitionError(Exception):
    pass


class StateMachine:
    """Generic table-driven state machine. Any future lifecycle entity (Quote approval, Site
    lifecycle) should define its own transition graph and reuse this engine rather than
    hand-rolling per-entity if/elif chains.

    Blueprint Part 23 requires every transition to record actor/timestamp/event -- handled here
    generically via app.domain.events.record_event, so no per-entity wiring is needed for that
    part either. Required conditions / warnings / blocks / overrides (the rest of Part 23) are
    deliberately NOT built yet -- this is just the base transition graph, which is what Phase 0
    needs to exist before anything depends on it (same spirit as Sprint 0.3's revision pattern).
    """

    def __init__(self, transitions: dict[str, set[str]]):
        self.transitions = transitions

    def can_transition(self, from_state: str, to_state: str) -> bool:
        return to_state in self.transitions.get(from_state, set())

    def transition(
        self,
        session,
        obj,
        entity_type: str,
        to_state: str,
        actor_user_id=None,
        payload: dict | None = None,
    ) -> None:
        from_state = obj.state
        if not self.can_transition(from_state, to_state):
            raise InvalidTransitionError(
                f"Cannot transition {entity_type} from {from_state!r} to {to_state!r}"
            )
        obj.state = to_state
        session.flush()
        record_event(
            session,
            entity_type,
            obj.id,
            "state_transition",
            {"from": from_state, "to": to_state, **(payload or {})},
            actor_user_id,
        )
