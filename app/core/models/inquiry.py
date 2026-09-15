import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class WebsiteInquiry(Base):
    """A raw public contact-form submission -- deliberately NOT an Opportunity. Opportunity
    requires a Site to already exist (Part 26: "a Site must already exist for there to be
    anything concrete to survey/quote against"), but a website visitor filling out a contact
    form has no Site on record yet. This is the step before that: an unqualified lead a staff
    member reviews and, if it's real, turns into a Site + Opportunity by hand.
    `converted_to_opportunity_id` records that triage decision once made; nothing else about
    this table assumes every row will become one.
    """

    __tablename__ = "website_inquiries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_interest: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    converted_to_opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("opportunities.id"), nullable=True
    )
