import uuid

from app.core.models.event import Event


def record_event(
    session,
    entity_type: str,
    entity_id: uuid.UUID,
    event_type: str,
    payload: dict | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> Event:
    event = Event(
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        payload=payload or {},
        actor_user_id=actor_user_id,
    )
    session.add(event)
    session.flush()
    return event
