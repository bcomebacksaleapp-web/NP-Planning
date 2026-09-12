import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow

# C10, verbatim: "Some customers/sites may be strategically poor" -- these are the examples the
# Blueprint itself gives, not a claim that this is the only possible set, but nothing invented
# beyond what's listed.
SITE_QUALITY_FLAG_TYPES = (
    "BAD_PAYMENT",
    "REPEATED_SCOPE_ABUSE",
    "MARGIN_LEAKAGE",
    "HIGH_DISPUTE",
    "EXCESSIVE_ADMIN_BURDEN",
    "UNSAFE_PRACTICES",
    "POOR_CAPACITY_FIT",
)
SiteQualityFlagType = Enum(
    *SITE_QUALITY_FLAG_TYPES, name="site_quality_flag_type", native_enum=False, create_constraint=True
)


class SiteQualityFlag(Base):
    """C10: Optimize good sites, not maximum job count. A flag is a fact someone recorded about
    a site being strategically poor in some specific way -- it does not itself compute a
    "healthy site score". The Blueprint gives no formula for a graded health score here, so
    Business Mode's Healthy Sites view (app.domain.site_quality.is_healthy) is deliberately
    binary: no unresolved flags means healthy, not a weighted composite.
    """

    __tablename__ = "site_quality_flags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    flag_type: Mapped[str] = mapped_column(SiteQualityFlagType, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    flagged_by: Mapped[str] = mapped_column(String(128), nullable=False)
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
