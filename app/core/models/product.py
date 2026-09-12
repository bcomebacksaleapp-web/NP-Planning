import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow


class Product(Base):
    """A product line, e.g. "CANOPY" (Part 22's first hero product). Deliberately no pricing or
    quantity logic here -- that all lives in RecipeVersion.formula so it can be versioned.
    """

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recipes: Mapped[list["ProductRecipe"]] = relationship(back_populates="product")


class ProductRecipe(Base):
    """The 'current' half of the current-row + append-only-revision-table pattern (same shape as
    Project/ProjectRevision from Sprint 0.3) -- reuses app.domain.revisioning directly rather
    than reinventing per-entity numbering, which is exactly the reuse that sprint's docstring
    anticipated.
    """

    __tablename__ = "product_recipes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="recipes")
    versions: Mapped[list["RecipeVersion"]] = relationship(back_populates="recipe")


class RecipeVersion(Base):
    """Append-only. `formula` is deliberately an opaque JSON blob for now -- Sprint 1.1 builds the
    versioned container, not the Canopy takeoff math itself (roof area / gutter / flashing
    formulas, waste factors, labor productivity rates). Those are real business facts that have
    to come from the business, not be invented here (Law 9; Part 28: don't fabricate engineering
    evidence) -- this table is what they'll be stored in once they're supplied.
    """

    __tablename__ = "recipe_versions"
    __table_args__ = (UniqueConstraint("recipe_id", "version_number", name="uq_recipe_version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_recipes.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    formula: Mapped[dict] = mapped_column(JSON, nullable=False)
    restored_from_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    recipe: Mapped["ProductRecipe"] = relationship(back_populates="versions")
