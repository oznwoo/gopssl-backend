from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date
from schemas.treatment import Treatment

# -------- SaleTreatment --------

class SaleTreatmentBase(BaseModel):
    treatment_id: int
    price: int

class SaleTreatmentCreate(SaleTreatmentBase):
    pass

class SaleTreatment(SaleTreatmentBase):
    id: int
    sale_id: int
    treatment: Treatment

    class Config:
        orm_mode = True

# -------- Sale --------

class SaleCreate(BaseModel):
    user_id: int
    customer_id: int
    sale_date: date
    detail: Optional[str]
    payment_type: Optional[str]
    total_amount: Optional[int]
    treatments: List[SaleTreatmentCreate]
    extra_prices: Optional[Dict[str, int]] = {}  # ✅ 기장추가를 카테고리 기준으로 받음

class SaleRead(BaseModel):
    id: int
    user_id: int
    customer_id: int
    sale_date: date
    detail: Optional[str]
    payment_type: Optional[str]
    total_amount: Optional[int]
    created_at: datetime
    treatments: List[SaleTreatment]
    extra_prices: Optional[Dict[str, int]] = {}

    class Config:
        orm_mode = True