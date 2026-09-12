import uuid

from app.core.db import utcnow
from app.core.models.critical_spec import CriticalSpec
from app.domain.state_machine import StateMachine

# C5's own chain, strictly forward -- Discussion -> Proposed -> Confirmed. No backward transition
# is modeled (e.g. Proposed -> Discussion) since the Blueprint doesn't state one; add it only if
# a real workflow need shows up, not speculatively.
CRITICAL_SPEC_TRANSITIONS: dict[str, set[str]] = {
    "DISCUSSION": {"PROPOSED"},
    "PROPOSED": {"CONFIRMED"},
}

CRITICAL_SPEC_STATE_MACHINE = StateMachine(CRITICAL_SPEC_TRANSITIONS)


def transition_critical_spec(
    session,
    spec: CriticalSpec,
    to_state: str,
    actor_user_id: uuid.UUID | None = None,
    confirmed_by: str | None = None,
) -> None:
    CRITICAL_SPEC_STATE_MACHINE.transition(session, spec, "critical_spec", to_state, actor_user_id)
    if to_state == "CONFIRMED":
        spec.confirmed_by = confirmed_by
        spec.confirmed_at = utcnow()
        session.flush()
