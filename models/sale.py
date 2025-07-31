from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    sale_date = Column(Date, nullable=False)
    detail = Column(Text)
    payment_type = Column(String(20))
    total_amount = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    extra_prices = Column(JSON, nullable=True) 
    customer = relationship("Customer", back_populates="sales")
    treatments = relationship("SaleTreatment", back_populates="sale", cascade="all, delete")



class SaleTreatment(Base):
    __tablename__ = "sale_treatments"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    treatment_id = Column(Integer, ForeignKey("treatments.id", ondelete="SET NULL"), nullable=True)
    
    price = Column(Integer, nullable=False)  # 기본 시술 가격

    sale = relationship("Sale", back_populates="treatments")
    treatment = relationship("Treatment", back_populates="sale_treatments")