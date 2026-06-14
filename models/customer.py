from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from database.session import Base
from sqlalchemy.orm import relationship

class Customer(Base):
  __tablename__ = "customers"

  id = Column(Integer, primary_key=True, index=True)
  user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
  name = Column(String(50), default="신규고객님")
  phone_number = Column(String(20))
  detail = Column(Text)
  created_at = Column(DateTime(timezone=True), server_default=func.now())
  is_deleted = Column(Boolean, default=False, nullable=False)
  deleted_at = Column(DateTime(timezone=True), nullable=True)

  sales = relationship("Sale", back_populates="customer")