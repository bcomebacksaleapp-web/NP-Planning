from sqlalchemy import select

from app.core.models.identity import Permission, RolePermission

ACTION_LEVEL_RANK = {"READ": 0, "SUGGEST": 1, "DRAFT": 2, "COMMIT": 3}


def has_permission(session, role_id, resource: str, required_level: str) -> bool:
    """True if `role_id` has been granted `required_level` (or a stronger one) on `resource`.

    A COMMIT grant satisfies a READ requirement; a READ grant does not satisfy a COMMIT
    requirement. This encodes the platform's fixed action-level ordering (Part 24): AI may
    READ/SUGGEST/DRAFT, but consequential COMMIT actions require it explicitly.

    Deliberately just the domain-logic check for Phase 0 -- NOT wired into FastAPI request
    handling yet. There are no real endpoints to protect beyond /health, and bolting on a
    placeholder "trust this header" current-user resolution would look like security without
    being any, which is worse than not having it. Wire this into request handling only once
    real authenticated endpoints (and real login/session infrastructure) exist.
    """
    if required_level not in ACTION_LEVEL_RANK:
        raise ValueError(f"Unknown action level: {required_level!r}")

    granted_levels = session.execute(
        select(Permission.action_level)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id, Permission.resource == resource)
    ).scalars().all()

    if not granted_levels:
        return False
    return max(ACTION_LEVEL_RANK[level] for level in granted_levels) >= ACTION_LEVEL_RANK[required_level]
