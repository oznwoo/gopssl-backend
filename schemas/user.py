from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# 회원가입 요청용 (입력 스키마)
class UserCreate(BaseModel):
  name: Optional[str]
  email: EmailStr
  password: str
  store_name: Optional[str]
  address: Optional[str]
  address_detail: Optional[str]

# 유저 조회 응답용 (출력 스키마)
class UserRead(BaseModel):
  id: int
  name: Optional[str]
  email: EmailStr
  store_name: Optional[str]
  address: Optional[str]
  address_detail: Optional[str]
  created_at: datetime

  class Config: 
    orm_mode: True


class Token(BaseModel):
    access_token: str
    token_type: str
  