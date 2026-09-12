# Import every model module here so Base.metadata is fully populated for Alembic autogenerate --
# a model that isn't imported is invisible to `alembic revision --autogenerate` and its table
# would silently never get created.
from app.core.models.identity import Permission, Role, RolePermission, User  # noqa: F401
from app.core.models.party import Customer, Site  # noqa: F401
from app.core.models.project import Project, ProjectRevision  # noqa: F401
from app.core.models.event import Event  # noqa: F401
from app.core.models.feature_flag import FeatureFlag  # noqa: F401
from app.core.models.product import Product, ProductRecipe, RecipeVersion  # noqa: F401
