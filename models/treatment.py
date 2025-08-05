from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base

class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    default_price = Column(Integer, nullable=False)

    sale_treatments = relationship("SaleTreatment", back_populates="treatment")