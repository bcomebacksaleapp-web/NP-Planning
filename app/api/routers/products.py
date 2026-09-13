import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.product import Product

router = APIRouter(prefix="/products", tags=["products"])


class ProductResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str


@router.get("", response_model=list[ProductResponse])
def list_products_route(
    db: Session = Depends(get_db), user=Depends(require_permission("product_recipe", "READ"))
) -> list[ProductResponse]:
    """Discoverability gap found while exercising the API end-to-end: there was no way to find
    a Product's id at all (e.g. to then call POST /recipes) short of querying the database
    directly. Read-only, so gated at READ rather than DRAFT like the write endpoints in this
    same domain area."""
    products = db.execute(select(Product)).scalars().all()
    return [ProductResponse(id=p.id, code=p.code, name=p.name) for p in products]
