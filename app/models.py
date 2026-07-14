from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DecisionAnalysis(Base):
    __tablename__ = "decision_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    context_preview: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class LibraryAsset(Base):
    __tablename__ = "library_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class DeletedAsset(Base):
    __tablename__ = "deleted_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    cpf: Mapped[str] = mapped_column(String(14), nullable=False, default="")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    zip_code: Mapped[str] = mapped_column(String(9), nullable=False, default="")
    street: Mapped[str] = mapped_column(String(180), nullable=False, default="")
    number: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    complement: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    lot: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    block: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    building: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    apartment: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    neighborhood: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(2), nullable=False, default="")
    completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class UserAvatar(Base):
    __tablename__ = "user_avatars"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class BillingAccount(Base):
    __tablename__ = "billing_accounts"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="unselected")
    subscription_status: Mapped[str] = mapped_column(String(32), nullable=False, default="inactive")
    plan_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    stripe_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class ProcessedStripeEvent(Base):
    __tablename__ = "processed_stripe_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ActiveChatState(Base):
    __tablename__ = "active_chat_states"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    messages_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    active_operation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class DiagnosisState(Base):
    __tablename__ = "diagnosis_states"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    operation: Mapped[str | None] = mapped_column(String(180), nullable=True)
    state_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_user_feedbacks_rating"),
        CheckConstraint(
            "category IN ('suggestion', 'problem', 'praise')",
            name="ck_user_feedbacks_category",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="received", index=True)
    admin_hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class OperationalEvent(Base):
    __tablename__ = "operational_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    module: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="error", index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="backend")
    path: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    method: Mapped[str] = mapped_column(String(12), nullable=False, default="")
    occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
