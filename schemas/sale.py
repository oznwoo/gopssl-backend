from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date

# -------- SaleTreatment --------

class SaleTreatmentBase(BaseModel):
    treatment_id: int
    price: int

class SaleTreatmentCreate(SaleTreatmentBase):
    pass

class SaleTreatmentRead(SaleTreatmentBase):
    id: int
    sale_id: int
    treatment_name: str

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
    extra_prices: Optional[Dict[str, int]] = {}

class SaleUpdate(SaleCreate):
    id: int

class SaleRead(BaseModel):
    id: int
    user_id: int
    customer_id: int
    customer_name: str 
    sale_date: date
    detail: Optional[str]
    payment_type: Optional[str]
    total_amount: Optional[int]
    created_at: datetime
    treatments: List[SaleTreatmentRead]  
    extra_prices: Optional[Dict[str, int]] = {}
    num_of_visits: Optional[int]
    first_visit: Optional[date] = None 
    previous_visit: Optional[date] = None 

    model_config = {
        "from_attributes": True
    }