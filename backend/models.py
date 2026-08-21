from datetime import date, datetime

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# All primary/foreign keys are nvarchar(20) string IDs in the real database
# (e.g. 'u001', 'c001'/'v001', 's001', 'r001') — not autoincrement integers.
# Verified live against beyondportal-db on 2026-08-20.


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(200))
    persona: Mapped[str] = mapped_column(String(100))
    declared_interests: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column()


class ContentItem(Base):
    __tablename__ = "content_items"

    content_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(300))
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    blob_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    topic_tags: Mapped[str] = mapped_column(Text)
    published_at: Mapped[date] = mapped_column(Date)


class EngagementSignal(Base):
    __tablename__ = "engagement_signal"

    signal_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    content_id: Mapped[str] = mapped_column(ForeignKey("content_items.content_id"))
    signal_type: Mapped[str] = mapped_column(String(50))
    depth_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column()


class EngagementScore(Base):
    __tablename__ = "engagement_scores"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    score: Mapped[float] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(50))
    delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_updated: Mapped[datetime] = mapped_column()


class Recommendation(Base):
    __tablename__ = "recommendations"

    rec_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    content_id: Mapped[str] = mapped_column(ForeignKey("content_items.content_id"))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    reason_code: Mapped[str] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    generated_at: Mapped[datetime] = mapped_column()


class SignalWeightConfig(Base):
    __tablename__ = "signal_weight_config"

    signal_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    weight: Mapped[int] = mapped_column(Integer)
