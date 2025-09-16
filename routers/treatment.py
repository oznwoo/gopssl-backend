from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from models.treatment import Treatment as TreatmentModel
from models.user import User as UserModel
from schemas.treatment import Treatment, TreatmentCreate
from dependencies import get_current_user

router = APIRouter(
    prefix="/treatments",
    tags=["treatments"],
)

# 모든 시술 조회
@router.get("/", response_model=List[Treatment])
def get_all_treatments(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    treatments = db.query(TreatmentModel).filter(TreatmentModel.user_id == current_user.id).all()
    
    # category_name 매핑
    result = []
    for t in treatments:
        result.append({
            "id": t.id,
            "name": t.name,
            "default_price": t.default_price,
            "category_id": t.category.id if t.category else None,
            "category_name": t.category.name if t.category else None
        })
    return result

# 단일 시술 조회
@router.get("/{treatment_id}", response_model=Treatment)
def get_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    t = db.query(TreatmentModel).filter(
        TreatmentModel.id == treatment_id,
        TreatmentModel.user_id == current_user.id
    ).first()
    
    if not t:
        raise HTTPException(status_code=404, detail="Treatment not found")
    
    return {
        "id": t.id,
        "name": t.name,
        "default_price": t.default_price,
        "category_id": t.category.id if t.category else None,
        "category_name": t.category.name if t.category else None
    }

# 시술 생성
@router.post("/", response_model=Treatment, status_code=status.HTTP_201_CREATED)
def create_treatment(
    treatment: TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_treatment = TreatmentModel(
        name=treatment.name,
        category_id=treatment.category_id,
        default_price=treatment.default_price,
        user_id=current_user.id
    )
    db.add(db_treatment)
    db.commit()
    db.refresh(db_treatment)

    return {
        "id": db_treatment.id,
        "name": db_treatment.name,
        "default_price": db_treatment.default_price,
        "category_id": db_treatment.category.id if db_treatment.category else None,
        "category_name": db_treatment.category.name if db_treatment.category else None
    }

# 시술 수정
@router.put("/{treatment_id}", response_model=Treatment, status_code=status.HTTP_201_CREATED)
def update_treatment(
    treatment_id: int,
    updated_data: TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    t = db.query(TreatmentModel).filter(
        TreatmentModel.id == treatment_id,
        TreatmentModel.user_id == current_user.id
    ).first()

    if not t:
        raise HTTPException(status_code=404, detail="Treatment not found")

    for key, value in updated_data.dict(exclude_unset=True).items():
        setattr(t, key, value)

    db.commit()
    db.refresh(t)

    return {
        "id": t.id,
        "name": t.name,
        "default_price": t.default_price,
        "category_id": t.category.id if t.category else None,
        "category_name": t.category.name if t.category else None
    }

# 시술 삭제
@router.delete("/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    t = db.query(TreatmentModel).filter(
        TreatmentModel.id == treatment_id,
        TreatmentModel.user_id == current_user.id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Treatment not found")
    db.delete(t)
    db.commit()