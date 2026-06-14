from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CustomerCreate(BaseModel):
  user_id: int
  name: Optional[str] = "신규"
  phone_number: Optional[str] = None
  detail: Optional[str] = None

class CustomerUpdate(CustomerCreate): 
  id: int

class CustomerRead(BaseModel):
  id: int
  user_id: int
  name: Optional[str]
  phone_number: Optional[str] = None
  detail: Optional[str] = None
  num_of_visits: Optional[int] = None
  created_at: datetime
  is_deleted: bool = False
  deleted_at: Optional[datetime] = None

  class Config:
      from_attributes = True


class DeletedCustomerRead(BaseModel):
  id: int
  name: Optional[str]
  detail: Optional[str] = None
  created_at: datetime
  deleted_at: Optional[datetime] = None

  class Config:
      from_attributes = True

