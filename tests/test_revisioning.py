from sqlalchemy import select

from app.core.models.party import Customer, Site
from app.core.models.project import ProjectRevision
from app.domain.projects import create_project, restore_project_revision, update_project
from app.domain.revisioning import latest_revision


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return site


def test_update_project_creates_new_revisions_without_touching_old_ones(session):
    site = _make_site(session)
    project = create_project(session, site.id, {"name": "v1"})
    update_project(session, project, {"name": "v2"})
    update_project(session, project, {"name": "v3"})
    session.commit()

    current = latest_revision(session, ProjectRevision, "project_id", project.id)
    assert current.revision_number == 3
    assert current.data == {"name": "v3"}

    revisions = _all_revisions(session, project.id)
    assert [r.revision_number for r in revisions] == [1, 2, 3]
    assert [r.data["name"] for r in revisions] == ["v1", "v2", "v3"]
    assert all(r.restored_from_revision_number is None for r in revisions)


def test_restore_creates_a_new_revision_and_leaves_history_untouched(session):
    """Blueprint Part 9 example, verbatim: Rev 12 -> Rev 13 -> Rev 14, restore Rev 12 creates
    Rev 15 based on Rev 12. Rev 12/13/14 are never rewritten (Law 4)."""
    site = _make_site(session)
    project = create_project(session, site.id, {"name": "v1"})  # revision 1 ("Rev 12" analog)
    update_project(session, project, {"name": "v2"})  # revision 2 ("Rev 13")
    update_project(session, project, {"name": "v3"})  # revision 3 ("Rev 14")
    session.commit()

    restored = restore_project_revision(session, project, target_revision_number=1)
    session.commit()

    # A NEW revision was created (4), not a rewind onto revision 1.
    assert restored.revision_number == 4
    assert restored.data == {"name": "v1"}
    assert restored.restored_from_revision_number == 1
    current = latest_revision(session, ProjectRevision, "project_id", project.id)
    assert current.id == restored.id

    # All four revisions coexist; the original three are byte-for-byte unchanged.
    revisions = _all_revisions(session, project.id)
    assert [r.revision_number for r in revisions] == [1, 2, 3, 4]
    assert revisions[0].data == {"name": "v1"}
    assert revisions[1].data == {"name": "v2"}
    assert revisions[2].data == {"name": "v3"}
    assert revisions[3].data == {"name": "v1"}
    assert revisions[3].restored_from_revision_number == 1
    assert revisions[0].restored_from_revision_number is None


def test_restoring_a_restored_revision_chains_correctly(session):
    """Restore-of-a-restore must still only ever append -- confirms the pattern doesn't special
    case "restoring a restore" incorrectly (e.g. by pointing at the original instead of the
    most recent restore)."""
    site = _make_site(session)
    project = create_project(session, site.id, {"name": "v1"})
    update_project(session, project, {"name": "v2"})
    session.commit()

    first_restore = restore_project_revision(session, project, target_revision_number=1)
    session.commit()
    assert first_restore.revision_number == 3

    second_restore = restore_project_revision(session, project, target_revision_number=first_restore.revision_number)
    session.commit()

    assert second_restore.revision_number == 4
    assert second_restore.restored_from_revision_number == 3
    assert second_restore.data == {"name": "v1"}


def _all_revisions(session, project_id) -> list[ProjectRevision]:
    return list(
        session.execute(
            select(ProjectRevision)
            .where(ProjectRevision.project_id == project_id)
            .order_by(ProjectRevision.revision_number)
        ).scalars()
    )
