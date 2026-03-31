import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(45))
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ping_interval: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ping_results: Mapped[list["PingResult"]] = relationship(back_populates="server", cascade="all, delete-orphan")
    daily_availabilities: Mapped[list["DailyAvailability"]] = relationship(back_populates="server", cascade="all, delete-orphan")


from app.models.ping_result import DailyAvailability, PingResult  # noqa: E402
