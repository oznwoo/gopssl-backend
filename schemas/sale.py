from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

# SaleTreatment
class SaleTreatmentCreate(BaseModel):
  treatment_name: str
  price: int

class SaleTreatmentRead(BaseModel):
  id: int

  class Config:
    orm_mode = True


# Sale
class SaleCreate(BaseModel):
  user_id: int
  customer_id: int
  sale_date: date
  detail: Optional[str]
  payment_type: Optional[str]
  total_amount: Optional[int]
  treatments: List[SaleTreatmentCreate]

class SaleRead(BaseModel):
  id: int
  user_id: int
  customer_id: int
  sale_date: date
  detail: Optional[str]
  payment_type: Optional[str]
  total_amount: Optional[int]
  created_at: datetime
  treatments: List[SaleTreatmentCreate]

  class Config:
    orm_mode = True