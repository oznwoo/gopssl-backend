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

  class Config:
      from_attributes = True 

