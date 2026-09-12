"""Generic archive/unarchive for any model with an `archived_at` column (Law 5: never hard-delete
business history by default; archive instead). Duck-typed on purpose -- no mixin/base class,
since the whole operation is two lines and every model already declares its own archived_at.

Deliberately does not cascade: archiving a Customer does not touch its Sites, archiving a Site
does not touch its Projects. A Site outliving a closed Project (Blueprint Part 15) is the same
principle one level up -- archiving a parent is a fact about the parent, not an instruction to
the children.

Hard delete is explicitly out of scope here. Law 5 allows it only for explicit legal/privacy/
retention requirements, and no such requirement exists yet -- add it when one actually does,
not speculatively.
"""

from app.core.db import utcnow


def archive(session, obj) -> None:
    """Idempotent: archiving an already-archived row is a no-op, not a timestamp bump."""
    if obj.archived_at is not None:
        return
    obj.archived_at = utcnow()
    session.flush()


def unarchive(session, obj) -> None:
    obj.archived_at = None
    session.flush()


def is_archived(obj) -> bool:
    return obj.archived_at is not None
