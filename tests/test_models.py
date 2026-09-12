import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.party import Customer, Site

# `session` fixture lives in tests/conftest.py -- shared with tests/test_revisioning.py.


def test_user_requires_unique_email(session):
    role = Role(code="OWNER_ADMIN", name="Owner / Admin")
    session.add(role)
    session.flush()

    session.add(User(email="a@example.com", name="First", role_id=role.id))
    session.flush()

    session.add(User(email="a@example.com", name="Second", role_id=role.id))
    with pytest.raises(IntegrityError):
        session.flush()


def test_site_rejects_unknown_customer(session):
    session.add(Site(customer_id=uuid.uuid4(), site_type="FACTORY", name="Ghost Site"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_site_type_rejects_value_outside_fixed_vocabulary(session):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()

    session.add(Site(customer_id=customer.id, site_type="SPACESHIP", name="Not a real type"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_role_permission_link_is_queryable_both_ways(session):
    role = Role(code="ESTIMATOR", name="Estimator")
    permission = Permission(resource="quote", action_level="DRAFT")
    session.add_all([role, permission])
    session.flush()

    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.commit()

    session.refresh(role)
    session.refresh(permission)
    assert permission in role.permissions
    assert role in permission.roles


def test_customer_archive_uses_soft_delete_not_hard_delete(session):
    """Law 5: archive, never hard-delete. This just confirms the column exists and round-trips
    -- the actual archive workflow (who/why/when) is a Sprint 0.4 concern, not modeled yet."""
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    assert customer.archived_at is None
