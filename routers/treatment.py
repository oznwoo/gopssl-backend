from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from models.treatment import Treatment as TreatmentModel
from schemas.treatment import Treatment, TreatmentCreate
from models.user import User as UserModel
from dependencies import get_current_user  # 위에서 만든 get_current_user

router = APIRouter(
    prefix="/treatments",
    tags=["treatments"],
)

# 모든 시술 조회 (현재 로그인한 사용자 기준)
@router.get("/", response_model=List[Treatment])
def get_all_treatments(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return db.query(TreatmentModel).filter(TreatmentModel.user_id == current_user.id).all()


# 단일 시술 조회 (현재 로그인한 사용자 기준)
@router.get("/{treatment_id}", response_model=Treatment)
def get_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    treatment = db.query(TreatmentModel).filter(
        TreatmentModel.id == treatment_id,
        TreatmentModel.user_id == current_user.id
    ).first()
    if not treatment:
        raise HTTPException(status_code=404, detail="Treatment not found")
    return treatment


# 시술 생성 (자동으로 user_id 지정)
@router.post("/", response_model=Treatment, status_code=status.HTTP_201_CREATED)
def create_treatment(
    treatment: TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_treatment = TreatmentModel(**treatment.dict(), user_id=current_user.id)
    db.add(db_treatment)
    db.commit()
    db.refresh(db_treatment)
    return db_treatment


# 시술 수정 (자동으로 user_id 지정)
@router.put("/{treatment_id}", response_model=Treatment, status_code=status.HTTP_201_CREATED)
def update_treatment(
    treatment_id: int,
    updated_data: TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    treatment = db.query(TreatmentModel).filter(
            TreatmentModel.id == treatment_id,
            TreatmentModel.user_id == current_user.id
        ).first()

    if not treatment:
        raise HTTPException(status_code=404, detail="Treatment not found")

    for key, value in updated_data.dict(exclude_unset=True).items():
        setattr(treatment, key, value)

    db.commit()
    db.refresh(treatment)
    return treatment



# 시술 삭제 (현재 로그인한 사용자만 삭제 가능)
@router.delete("/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    treatment = db.query(TreatmentModel).filter(
        TreatmentModel.id == treatment_id,
        TreatmentModel.user_id == current_user.id
    ).first()
    if not treatment:
        raise HTTPException(status_code=404, detail="Treatment not found")
    db.delete(treatment)
    db.commit()