# Import every model module here so Base.metadata is fully populated for Alembic autogenerate --
# a model that isn't imported is invisible to `alembic revision --autogenerate` and its table
# would silently never get created.
from app.core.models.identity import Permission, Role, RolePermission, User  # noqa: F401
from app.core.models.party import Customer, Site  # noqa: F401
from app.core.models.project import Project, ProjectRevision  # noqa: F401
from app.core.models.event import Event  # noqa: F401
from app.core.models.feature_flag import FeatureFlag  # noqa: F401
from app.core.models.product import Product, ProductRecipe, RecipeVersion  # noqa: F401
from app.core.models.quote import Quote, QuoteLine, QuoteRevision  # noqa: F401
from app.core.models.supplier import Supplier, SupplierQuote  # noqa: F401
from app.core.models.survey import Survey, SurveyObservation  # noqa: F401
from app.core.models.opportunity import Opportunity  # noqa: F401
from app.core.models.critical_spec import CriticalSpec  # noqa: F401
from app.core.models.confirmation import Confirmation  # noqa: F401
from app.core.models.site_quality_flag import SiteQualityFlag  # noqa: F401
from app.core.models.website import WebsiteBranch, WebsitePage, WebsitePageRevision, WidgetInstance  # noqa: F401
from app.core.models.session_token import SessionToken  # noqa: F401
from app.core.models.inquiry import WebsiteInquiry  # noqa: F401
