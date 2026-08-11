"""Lead model — a "leave a request" submission from a visitor with no
account yet. There is no self-registration on this platform (every account
is admin-created via /auth/admin/users), so this is how a prospective
student's contact info actually reaches staff."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class LeadStatus:
    NEW = "new"
    CONTACTED = "contacted"
    CLOSED = "closed"


class Lead(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "leads"

    # Intake answers — all optional except the contact fields checked at the
    # schema level (need at least one of phone/email to be worth anything).
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    goal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    study_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    destination_country: Mapped[str | None] = mapped_column(String(255), nullable=True)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Indexed: crud.find_recent_by_contact() looks these up on every POST
    # /leads (the platform's one public unauthenticated write) to catch
    # double-submits and repeat spam before writing another row.
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(16), default=LeadStatus.NEW, nullable=False, index=True)
