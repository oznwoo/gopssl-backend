from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict

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
    return db.query(TreatmentModel).filter(
        TreatmentModel.user_id == current_user.id
    ).order_by(TreatmentModel.category_id, TreatmentModel.display_order).all()


# 단일 시술 조회
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

# 시술 생성
@router.post("/", response_model=Treatment, status_code=status.HTTP_201_CREATED)
def create_treatment(
    treatment: TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # display_order 계산: 해당 카테고리의 시술 개수 + 1
    new_order = db.query(TreatmentModel).filter(
        TreatmentModel.user_id == current_user.id,
        TreatmentModel.category_id == treatment.category_id
    ).count() + 1

    db_treatment = TreatmentModel(
        name=treatment.name,
        category_id=treatment.category_id,
        default_price=treatment.default_price,
        user_id=current_user.id,
        display_order=new_order
    )
    db.add(db_treatment)
    db.commit()
    db.refresh(db_treatment)

    return db_treatment

# 시술 수정
@router.put("/{treatment_id}", response_model=Treatment)
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
    return t

# 시술 삭제
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

    deleted_order = treatment.display_order
    category_id = treatment.category_id

    db.delete(treatment)
    db.commit()

    # 삭제된 시술보다 순서가 뒤에 있는 시술들의 display_order를 1씩 감소
    db.query(TreatmentModel).filter(
        TreatmentModel.user_id == current_user.id,
        TreatmentModel.category_id == category_id,
        TreatmentModel.display_order > deleted_order
    ).update({"display_order": TreatmentModel.display_order - 1}, synchronize_session=False)
    db.commit()

@router.post("/reorder", status_code=status.HTTP_200_OK)
def reorder_treatments(
    order_data: Dict[int, int], # {treatment_id: new_order}
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """시술 순서를 업데이트합니다."""
    with db.begin():
        for treatment_id, new_order in order_data.items():
            treatment = db.query(TreatmentModel).filter_by(id=treatment_id, user_id=current_user.id).first()
            if treatment:
                treatment.display_order = new_order
    return {"message": "Treatments reordered successfully"}