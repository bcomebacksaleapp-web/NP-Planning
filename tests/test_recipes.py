from app.core.models.product import Product, RecipeVersion
from app.domain.recipes import create_recipe, restore_recipe_version, update_recipe
from app.domain.revisioning import latest_revision


def _make_product(session) -> Product:
    product = Product(code="CANOPY", name="Canopy")
    session.add(product)
    session.flush()
    return product


def test_create_recipe_creates_version_one(session):
    product = _make_product(session)
    recipe = create_recipe(session, product.id, "Canopy Standard", {"placeholder": True})
    session.commit()

    current = latest_revision(session, RecipeVersion, "recipe_id", recipe.id, "version_number")
    assert current.version_number == 1
    assert current.formula == {"placeholder": True}


def test_update_recipe_creates_a_new_version_without_touching_the_old_one(session):
    product = _make_product(session)
    recipe = create_recipe(session, product.id, "Canopy Standard", {"waste_factor": 0.05})
    update_recipe(session, recipe, {"waste_factor": 0.08})
    session.commit()

    versions = (
        session.query(RecipeVersion)
        .filter_by(recipe_id=recipe.id)
        .order_by(RecipeVersion.version_number)
        .all()
    )
    assert [v.version_number for v in versions] == [1, 2]
    assert versions[0].formula == {"waste_factor": 0.05}
    assert versions[1].formula == {"waste_factor": 0.08}


def test_restore_recipe_version_creates_a_new_version_and_leaves_history_untouched(session):
    """Same Law 4 guarantee as ProjectRevision, proven with the second real consumer of the
    generic revisioning helpers -- version_number, not revision_number, and it still works."""
    product = _make_product(session)
    recipe = create_recipe(session, product.id, "Canopy Standard", {"waste_factor": 0.05})
    update_recipe(session, recipe, {"waste_factor": 0.08})
    session.commit()

    restored = restore_recipe_version(session, recipe, target_version_number=1)
    session.commit()

    assert restored.version_number == 3
    assert restored.formula == {"waste_factor": 0.05}
    assert restored.restored_from_version_number == 1

    versions = (
        session.query(RecipeVersion)
        .filter_by(recipe_id=recipe.id)
        .order_by(RecipeVersion.version_number)
        .all()
    )
    assert [v.version_number for v in versions] == [1, 2, 3]
    assert versions[0].formula == {"waste_factor": 0.05}  # untouched
    assert versions[1].formula == {"waste_factor": 0.08}  # untouched
