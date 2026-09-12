import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models.product import Product, ProductRecipe, RecipeVersion
from app.domain.events import record_event
from app.domain.revisioning import next_revision_number

_NUMBER_ATTR = "version_number"


def get_or_create_product(session: Session, code: str, name: str) -> Product:
    """Idempotent on `code` -- callers that just need "the Product row for CANOPY" (e.g. the
    canopy configurator tagging its quote lines) shouldn't have to separately track whether
    it's been created yet."""
    product = session.execute(select(Product).where(Product.code == code)).scalar_one_or_none()
    if product is not None:
        return product
    product = Product(code=code, name=name)
    session.add(product)
    session.flush()
    return product


def create_recipe(
    session: Session, product_id: uuid.UUID, name: str, formula: dict, actor_user_id: uuid.UUID | None = None
) -> ProductRecipe:
    recipe = ProductRecipe(product_id=product_id, name=name)
    session.add(recipe)
    session.flush()

    session.add(RecipeVersion(recipe_id=recipe.id, version_number=1, formula=formula))
    session.flush()
    record_event(session, "product_recipe", recipe.id, "created", {"version_number": 1}, actor_user_id)
    return recipe


def update_recipe(
    session: Session, recipe: ProductRecipe, formula: dict, actor_user_id: uuid.UUID | None = None
) -> RecipeVersion:
    """Creates a new version holding `formula`. Never mutates an existing RecipeVersion row."""
    version_number = next_revision_number(session, RecipeVersion, "recipe_id", recipe.id, _NUMBER_ATTR)
    version = RecipeVersion(recipe_id=recipe.id, version_number=version_number, formula=formula)
    session.add(version)
    session.flush()
    record_event(
        session, "product_recipe", recipe.id, "version_created", {"version_number": version_number}, actor_user_id
    )
    return version


def restore_recipe_version(
    session: Session, recipe: ProductRecipe, target_version_number: int, actor_user_id: uuid.UUID | None = None
) -> RecipeVersion:
    """Law 4: restoring an old version creates a NEW version copying its formula. Never touches
    the old row."""
    target = session.execute(
        select(RecipeVersion).where(
            RecipeVersion.recipe_id == recipe.id,
            RecipeVersion.version_number == target_version_number,
        )
    ).scalar_one()

    new_version_number = next_revision_number(session, RecipeVersion, "recipe_id", recipe.id, _NUMBER_ATTR)
    version = RecipeVersion(
        recipe_id=recipe.id,
        version_number=new_version_number,
        formula=dict(target.formula),
        restored_from_version_number=target.version_number,
    )
    session.add(version)
    session.flush()
    record_event(
        session,
        "product_recipe",
        recipe.id,
        "version_restored",
        {"version_number": new_version_number, "restored_from_version_number": target.version_number},
        actor_user_id,
    )
    return version
