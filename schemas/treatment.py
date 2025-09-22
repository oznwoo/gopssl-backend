from pydantic import BaseModel

# -----------------------
# Treatment 관련 스키마
# -----------------------
class TreatmentBase(BaseModel):
    name: str
    category_id: int  # 나중에 Category ID를 사용하도록 바꾸면 int로 변경 가능
    default_price: int

class TreatmentCreate(TreatmentBase):
    pass

class Treatment(TreatmentBase):
    id: int
    display_order: int

    class Config:
        from_attributes = True


# -----------------------
# TreatmentCategory 관련 스키마
# -----------------------
class TreatmentCategoryBase(BaseModel):
    name: str

class TreatmentCategoryCreate(TreatmentCategoryBase):
    pass

class TreatmentCategory(TreatmentCategoryBase):
    id: int
    display_order: int

    class Config:
        from_attributes = True