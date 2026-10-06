from sqlalchemy import Column, Integer, ForeignKey
from db.base import Base

class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    insulation_id = Column(Integer, ForeignKey("insulations.id"), nullable=False)
