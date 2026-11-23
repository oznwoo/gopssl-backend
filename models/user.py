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

  # 가입 시 약관·개인정보 처리방침 동의 기록 (만 14세 이상 확인 포함).
  # 기존 계정은 기록이 없으므로 nullable. 컬럼 추가는 docs/migrations/2026-11-signup-consent.sql
  terms_version = Column(Text, nullable=True)
  privacy_version = Column(Text, nullable=True)
  agreed_at = Column(DateTime(timezone=True), nullable=True)

  treatments = relationship("Treatment", back_populates="user", cascade="all, delete-orphan")