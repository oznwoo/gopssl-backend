from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TreatmentBase(BaseModel):
    name: str
    category: str
    default_price: int

class TreatmentCreate(TreatmentBase):
    pass

class Treatment(TreatmentBase):
    id: int

    class Config:
        orm_mode = True