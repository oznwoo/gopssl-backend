from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base

class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    default_price = Column(Integer, nullable=False)

    user = relationship("User", back_populates="treatments")  # User 모델과 연결
    sale_treatments = relationship("SaleTreatment", back_populates="treatment")