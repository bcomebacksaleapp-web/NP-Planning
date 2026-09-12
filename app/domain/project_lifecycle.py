import uuid

from app.core.models.project import PROJECT_STATES, Project
from app.domain.archiving import archive
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


def close_project(session, project: Project, actor_user_id: uuid.UUID | None = None) -> None:
    """C7: Project Closed does NOT mean Site Closed. Closing means walking through every
    remaining lifecycle state to reach LIFECYCLE (the state machine only allows one step at a
    time -- there's no shortcut past HANDOVER/KNOWLEDGE_HARVEST) and archiving the Project.

    It must never touch the Site, which is the long-lived parent (Part 15) that outlives any
    individual project. There is nothing to cascade here on purpose: Site has its own
    independent archived_at, untouched by this call.
    """
    current_index = PROJECT_STATES.index(project.state)
    for state in PROJECT_STATES[current_index + 1 :]:
        transition_project(session, project, state, actor_user_id)
    archive(session, project, actor_user_id)
