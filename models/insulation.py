from datetime import UTC, datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Insulation(Base):
    __tablename__ = "thermal_insulations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    coefficient = Column(Integer, nullable=False)
    description = Column(String(500), nullable=False)
    image_url = Column(String(255), nullable=False)
    video_url = Column(String(255), nullable=False)
    status = Column(Integer, default=2)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=True, default=utc_now)
    formed_at = Column(DateTime, nullable=True, default=utc_now)
    warehouse = Column(String(255), nullable=True)
