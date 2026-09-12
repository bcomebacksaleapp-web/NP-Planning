import pytest

from app.core.models.identity import Permission, Role, RolePermission
from app.domain.authorization import has_permission


def _grant(session, role_code: str, resource: str, action_level: str) -> Role:
    role = Role(code=role_code, name=role_code)
    permission = Permission(resource=resource, action_level=action_level)
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.commit()
    return role


def test_role_without_any_grant_is_denied(session):
    role = Role(code="CUSTOMER", name="Customer")
    session.add(role)
    session.flush()
    assert has_permission(session, role.id, "quote", "READ") is False


def test_exact_grant_matches_exact_requirement(session):
    role = _grant(session, "ESTIMATOR", "quote", "DRAFT")
    assert has_permission(session, role.id, "quote", "DRAFT") is True


def test_higher_grant_satisfies_a_lower_requirement(session):
    role = _grant(session, "OWNER_ADMIN", "quote", "COMMIT")
    assert has_permission(session, role.id, "quote", "READ") is True
    assert has_permission(session, role.id, "quote", "COMMIT") is True


def test_lower_grant_does_not_satisfy_a_higher_requirement(session):
    """A role that can only READ must not be treated as able to COMMIT (Law 14)."""
    role = _grant(session, "SITE_ENGINEER", "quote", "READ")
    assert has_permission(session, role.id, "quote", "COMMIT") is False


def test_grant_on_a_different_resource_does_not_leak_over(session):
    role = _grant(session, "PM", "project", "COMMIT")
    assert has_permission(session, role.id, "quote", "READ") is False


def test_unknown_action_level_raises(session):
    role = Role(code="PM", name="Project Manager")
    session.add(role)
    session.flush()
    with pytest.raises(ValueError):
        has_permission(session, role.id, "quote", "YOLO")
