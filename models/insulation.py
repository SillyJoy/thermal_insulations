from sqlalchemy import Column, Integer, String, ForeignKey
from db.base import Base


class Insulation(Base):
    __tablename__ = "insulations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    coefficient = Column(Integer, nullable=False)
    description = Column(String(500), nullable=False)
    image_url = Column(String(255), nullable=False)
    video_url = Column(String(255), nullable=False)
    status = Column(Integer, default=2)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
