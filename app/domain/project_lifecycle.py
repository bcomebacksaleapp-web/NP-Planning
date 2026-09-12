import uuid

from app.core.models.project import PROJECT_STATES, Project
from app.domain.state_machine import StateMachine

# Linear chain per Part 23 -- each state can only advance to the next one. Required conditions,
# warnings, blocks, and overrides (the rest of Part 23) are a later phase's concern; this is
# deliberately just the base transition graph, proven to work before anything depends on it.
PROJECT_TRANSITIONS: dict[str, set[str]] = {
    state: {PROJECT_STATES[i + 1]} for i, state in enumerate(PROJECT_STATES[:-1])
}

PROJECT_STATE_MACHINE = StateMachine(PROJECT_TRANSITIONS)


def transition_project(
    session, project: Project, to_state: str, actor_user_id: uuid.UUID | None = None
) -> None:
    PROJECT_STATE_MACHINE.transition(session, project, "project", to_state, actor_user_id)
