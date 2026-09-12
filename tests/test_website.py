from app.core.models.product import Product
from app.core.models.website import WebsitePageRevision
from app.domain.revisioning import latest_revision
from app.domain.website import create_branch, create_page, restore_page_revision, update_page


def test_create_branch_records_an_event(session):
    from app.core.models.event import Event

    branch = create_branch(session, "MAIN")
    session.commit()

    events = session.query(Event).filter_by(entity_type="website_branch", entity_id=branch.id).all()
    assert len(events) == 1


def test_branch_can_record_it_was_forked_from_another(session):
    main = create_branch(session, "MAIN")
    experiment = create_branch(session, "FACTORY-EXPERIMENT", forked_from_branch_id=main.id)
    session.commit()

    assert experiment.forked_from_branch_id == main.id


def test_create_page_creates_revision_one_with_widgets_in_order(session):
    branch = create_branch(session, "MAIN")
    page = create_page(
        session, branch.id, "home",
        widgets=[
            {"widget_type": "Hero", "order_index": 0},
            {"widget_type": "EstimateCTA", "order_index": 1, "content_source": "product:CANOPY"},
        ],
    )
    session.commit()

    current = latest_revision(session, WebsitePageRevision, "page_id", page.id)
    assert current.revision_number == 1
    assert [w.widget_type for w in current.widgets] == ["Hero", "EstimateCTA"]


def test_update_page_creates_new_revision_without_touching_old_widgets(session):
    branch = create_branch(session, "MAIN")
    page = create_page(session, branch.id, "home", widgets=[{"widget_type": "Hero", "order_index": 0}])
    update_page(session, page, widgets=[{"widget_type": "ServiceCards", "order_index": 0}])
    session.commit()

    revisions = (
        session.query(WebsitePageRevision).filter_by(page_id=page.id).order_by(WebsitePageRevision.revision_number).all()
    )
    assert [w.widget_type for w in revisions[0].widgets] == ["Hero"]
    assert [w.widget_type for w in revisions[1].widgets] == ["ServiceCards"]


def test_removing_a_widget_never_deletes_the_business_data_it_referenced(session):
    """Law 10: UI components never own canonical business data. Deleting a widget instance must
    NOT delete product/pricing/project/site/customer data -- proven here by creating a widget
    that references a real Product, then publishing a NEW revision with that widget removed
    entirely, and confirming the Product survives untouched."""
    product = Product(code="CANOPY", name="Canopy")
    session.add(product)
    session.flush()

    branch = create_branch(session, "MAIN")
    page = create_page(
        session, branch.id, "home",
        widgets=[{"widget_type": "EstimateCTA", "order_index": 0, "content_source": f"product:{product.code}"}],
    )
    # New revision with the widget removed entirely -- the old revision's WidgetInstance row
    # still exists in history (Law 4), but is no longer "current".
    update_page(session, page, widgets=[])
    session.commit()

    current = latest_revision(session, WebsitePageRevision, "page_id", page.id)
    assert current.widgets == []

    fetched_product = session.get(Product, product.id)
    assert fetched_product is not None
    assert fetched_product.code == "CANOPY"


def test_restore_page_revision_creates_new_revision_and_leaves_history_untouched(session):
    branch = create_branch(session, "MAIN")
    page = create_page(session, branch.id, "home", widgets=[{"widget_type": "Hero", "order_index": 0}])
    update_page(session, page, widgets=[{"widget_type": "ServiceCards", "order_index": 0}])
    session.commit()

    restored = restore_page_revision(session, page, target_revision_number=1)
    session.commit()

    assert restored.revision_number == 3
    assert [w.widget_type for w in restored.widgets] == ["Hero"]
    assert restored.restored_from_revision_number == 1

    revisions = (
        session.query(WebsitePageRevision).filter_by(page_id=page.id).order_by(WebsitePageRevision.revision_number).all()
    )
    assert [w.widget_type for w in revisions[1].widgets] == ["ServiceCards"]  # untouched
