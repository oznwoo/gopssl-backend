from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# 회원가입 요청용 (입력 스키마)
class UserCreate(BaseModel):
  name: str
  email: EmailStr
  password: str
  store_name: Optional[str] = None
  address: Optional[str] = None
  address_detail: Optional[str] = None
  zip_code: Optional[str] = None

class UserUpdate(BaseModel):
  name: Optional[str] = None
  email: Optional[EmailStr] = None
  password: Optional[str] = None
  store_name: Optional[str] = None
  address: Optional[str] = None
  address_detail: Optional[str] = None
  zip_code: Optional[str] = None

# 유저 조회 응답용 (출력 스키마)
class UserRead(BaseModel):
  id: int
  name: Optional[str]
  email: EmailStr
  store_name: Optional[str] = None
  address: Optional[str] = None
  address_detail: Optional[str] = None
  zip_code: Optional[str] = None
  created_at: datetime

  class Config: 
    orm_mode: True


class Token(BaseModel):
    access_token: str
    token_type: str
  