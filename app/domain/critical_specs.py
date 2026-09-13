import uuid

from app.core.db import utcnow
from app.core.models.critical_spec import CriticalSpec
from app.domain.events import record_event
from app.domain.state_machine import StateMachine

# C5's own chain, strictly forward -- Discussion -> Proposed -> Confirmed. No backward transition
# is modeled (e.g. Proposed -> Discussion) since the Blueprint doesn't state one; add it only if
# a real workflow need shows up, not speculatively.
CRITICAL_SPEC_TRANSITIONS: dict[str, set[str]] = {
    "DISCUSSION": {"PROPOSED"},
    "PROPOSED": {"CONFIRMED"},
}

CRITICAL_SPEC_STATE_MACHINE = StateMachine(CRITICAL_SPEC_TRANSITIONS)


def create_critical_spec(
    session,
    project_id: uuid.UUID,
    spec_type: str,
    description: str,
    actor_user_id: uuid.UUID | None = None,
) -> CriticalSpec:
    """Starts in DISCUSSION (CriticalSpec's default) -- every other entity's create_X function
    records a "created" event; this one didn't exist at all until this gap was found by trying
    to exercise the API end-to-end and discovering there was no way to create one through it,
    only construct it directly in tests (which silently skipped the event log)."""
    spec = CriticalSpec(project_id=project_id, spec_type=spec_type, description=description)
    session.add(spec)
    session.flush()
    record_event(session, "critical_spec", spec.id, "created", {"spec_type": spec_type}, actor_user_id)
    return spec


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
