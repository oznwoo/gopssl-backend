from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base

class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    default_price = Column(Integer, nullable=False)
    category_id = Column(Integer, ForeignKey("treatment_categories.id"), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="treatments")
    category = relationship("TreatmentCategory", back_populates="treatments")
    sale_treatments = relationship("SaleTreatment", back_populates="treatment")

class TreatmentCategory(Base):
    __tablename__ = "treatment_categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # 사용자별 카테고리 선택 가능
    name = Column(String, nullable=False)
    display_order = Column(Integer, nullable=False, default=0)


    user = relationship("User", backref="treatment_categories")
    treatments = relationship("Treatment", back_populates="category")