from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class CustomerCreate(BaseModel):
  user_id: int
  name: Optional[str] = "신규고객님"
  phone_number: Optional[str]
  detail: Optional[str]

class CustomerRead(BaseModel):
  id: int 
  user_id: int
  name: Optional[str]
  phone_number: Optional[str]
  detail: Optional[str]
  created_at: datetime

  class Config: 
    orm_mode = True
  