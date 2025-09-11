from pydantic import BaseModel


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