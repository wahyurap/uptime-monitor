import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PingResult(Base):
    __tablename__ = "ping_results"
    __table_args__ = (
        Index("ix_ping_results_server_timestamp", "server_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"))
    is_up: Mapped[bool] = mapped_column(Boolean)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    server: Mapped["Server"] = relationship(back_populates="ping_results")


class DailyAvailability(Base):
    __tablename__ = "daily_availability"
    __table_args__ = (
        Index("ix_daily_availability_server_date", "server_id", "date", unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    total_pings: Mapped[int] = mapped_column(Integer)
    success_pings: Mapped[int] = mapped_column(Integer)
    availability_pct: Mapped[float] = mapped_column(Float)
    avg_latency: Mapped[float | None] = mapped_column(Float, nullable=True)

    server: Mapped["Server"] = relationship(back_populates="daily_availabilities")


from app.models.server import Server  # noqa: E402
