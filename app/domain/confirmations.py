import uuid

from app.core.models.confirmation import Confirmation
from app.core.models.project import PROJECT_STATES, Project
from app.core.models.quote import Quote, QuoteRevision
from app.domain.events import record_event
from app.domain.project_lifecycle import transition_project
from app.domain.revisioning import latest_revision

_CONFIRMED_STATE = "CONFIRMED"


class ConfirmationBlockedError(Exception):
    pass


class ConfirmationRequiresOverrideReasonError(Exception):
    pass


def confirm_project(
    session,
    project: Project,
    quote: Quote,
    confirmed_by: str,
    override_reason: str | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> Confirmation:
    """Walks the project to CONFIRMED (Part 23) and records exactly which quote revision was
    confirmed and by whom -- Law 12: overrides require who (confirmed_by) and why
    (override_reason).

    A BLOCKED quote can never be confirmed through this path -- Part 5: no commercial override
    on a hard block. A quote requiring override (management/senior GM bands, C2; unverified
    quantity basis, C3; etc.) CAN be confirmed, but only with an explicit override_reason --
    silently confirming past an OVERRIDE_REQUIRED gate would defeat the entire point of having
    one.
    """
    if quote.project_id != project.id:
        raise ValueError("Quote does not belong to this project")

    current_quote_revision = latest_revision(session, QuoteRevision, "quote_id", quote.id)
    if current_quote_revision.gate_status == "BLOCKED":
        raise ConfirmationBlockedError(f"Cannot confirm: quote gate is BLOCKED ({current_quote_revision.gate_note})")
    if current_quote_revision.gate_status == "OVERRIDE_REQUIRED" and not override_reason:
        raise ConfirmationRequiresOverrideReasonError(
            f"Quote gate requires override ({current_quote_revision.gate_note}) -- override_reason is required"
        )

    current_index = PROJECT_STATES.index(project.state)
    target_index = PROJECT_STATES.index(_CONFIRMED_STATE)
    if current_index < target_index:
        for state in PROJECT_STATES[current_index + 1 : target_index + 1]:
            transition_project(session, project, state, actor_user_id)

    confirmation = Confirmation(
        project_id=project.id,
        quote_id=quote.id,
        confirmed_quote_revision_number=current_quote_revision.revision_number,
        confirmed_by=confirmed_by,
        override_reason=override_reason,
    )
    session.add(confirmation)
    session.flush()
    record_event(
        session,
        "confirmation",
        confirmation.id,
        "created",
        {
            "project_id": str(project.id),
            "quote_id": str(quote.id),
            "quote_revision_number": current_quote_revision.revision_number,
            "gate_status": current_quote_revision.gate_status,
        },
        actor_user_id,
    )
    return confirmation
