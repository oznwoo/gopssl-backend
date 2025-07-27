from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from schemas.treatment import Treatment  # ✅ 반드시 import

# -------- SaleTreatment --------

class SaleTreatmentBase(BaseModel):
    treatment_id: int
    price: int

class SaleTreatmentCreate(SaleTreatmentBase):
    pass

class SaleTreatment(SaleTreatmentBase):
    id: int
    sale_id: int
    treatment: Treatment  # ✅ nested 응답 시 Treatment 객체 포함

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

class SaleRead(BaseModel):
    id: int
    user_id: int
    customer_id: int
    sale_date: date
    detail: Optional[str]
    payment_type: Optional[str]
    total_amount: Optional[int]
    created_at: datetime
    treatments: List[SaleTreatment]  # ✅ 이게 맞음

    class Config:
        orm_mode = True