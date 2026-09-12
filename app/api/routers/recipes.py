import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.product import ProductRecipe, RecipeVersion
from app.domain.recipes import create_recipe, restore_recipe_version, update_recipe
from app.domain.revisioning import latest_revision

router = APIRouter(prefix="/recipes", tags=["recipes"])


class CreateRecipeRequest(BaseModel):
    product_id: uuid.UUID
    name: str
    formula: dict


class UpdateRecipeRequest(BaseModel):
    formula: dict


class RestoreRecipeVersionRequest(BaseModel):
    target_version_number: int


class RecipeVersionResponse(BaseModel):
    recipe_id: uuid.UUID
    version_number: int
    formula: dict
    restored_from_version_number: int | None


def _version_response(recipe_id: uuid.UUID, version: RecipeVersion) -> RecipeVersionResponse:
    return RecipeVersionResponse(
        recipe_id=recipe_id, version_number=version.version_number, formula=version.formula,
        restored_from_version_number=version.restored_from_version_number,
    )


@router.post("", response_model=RecipeVersionResponse)
def create_recipe_route(
    body: CreateRecipeRequest, db: Session = Depends(get_db), user=Depends(require_permission("product_recipe", "DRAFT"))
) -> RecipeVersionResponse:
    recipe = create_recipe(db, body.product_id, body.name, body.formula, actor_user_id=user.id)
    db.commit()
    current = latest_revision(db, RecipeVersion, "recipe_id", recipe.id, "version_number")
    return _version_response(recipe.id, current)


@router.put("/{recipe_id}", response_model=RecipeVersionResponse)
def update_recipe_route(
    recipe_id: uuid.UUID, body: UpdateRecipeRequest, db: Session = Depends(get_db),
    user=Depends(require_permission("product_recipe", "DRAFT")),
) -> RecipeVersionResponse:
    recipe = db.get(ProductRecipe, recipe_id)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")

    version = update_recipe(db, recipe, body.formula, actor_user_id=user.id)
    db.commit()
    return _version_response(recipe.id, version)


@router.post("/{recipe_id}/restore", response_model=RecipeVersionResponse)
def restore_recipe_route(
    recipe_id: uuid.UUID, body: RestoreRecipeVersionRequest, db: Session = Depends(get_db),
    user=Depends(require_permission("product_recipe", "DRAFT")),
) -> RecipeVersionResponse:
    recipe = db.get(ProductRecipe, recipe_id)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")

    version = restore_recipe_version(db, recipe, body.target_version_number, actor_user_id=user.id)
    db.commit()
    return _version_response(recipe.id, version)
