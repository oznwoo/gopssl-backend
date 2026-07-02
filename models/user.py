from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database.session import Base
from sqlalchemy.orm import relationship

class User(Base):
  __tablename__ = "users"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String(50), nullable=True)
  email = Column(String(100), unique=True, nullable=False)
  password = Column(Text, nullable=False)
  store_name = Column(String(100))
  address = Column(Text)
  address_detail = (Column(Text))
  zip_code = Column(Text)
  created_at = Column(DateTime(timezone=True), server_default=func.now())

  treatments = relationship("Treatment", back_populates="user", cascade="all, delete-orphan")