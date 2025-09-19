from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from models.treatment import TreatmentCategory as TreatmentCategoryModel
from schemas.treatment import TreatmentCategory, TreatmentCategoryCreate
from models.user import User as UserModel
from dependencies import get_current_user  # 현재 로그인 사용자 가져오는 함수

router = APIRouter(
    prefix="/categories",
    tags=["treatment_categories"],
)

# 모든 카테고리 조회 (현재 로그인한 사용자 기준)
@router.get("/", response_model=List[TreatmentCategory])
def get_all_categories(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return db.query(TreatmentCategoryModel).filter(
        TreatmentCategoryModel.user_id == current_user.id
    ).all()

# 단일 카테고리 조회
@router.get("/{category_id}", response_model=TreatmentCategory)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    category = db.query(TreatmentCategoryModel).filter(
        TreatmentCategoryModel.id == category_id,
        TreatmentCategoryModel.user_id == current_user.id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

# 카테고리 생성
@router.post("/", response_model=TreatmentCategory, status_code=status.HTTP_201_CREATED)
def create_category(
    category: TreatmentCategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_category = TreatmentCategoryModel(**category.dict(), user_id=current_user.id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

# 카테고리 수정
@router.put("/{category_id}", response_model=TreatmentCategory)
def update_category(
    category_id: int,
    updated_data: TreatmentCategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    category = db.query(TreatmentCategoryModel).filter(
        TreatmentCategoryModel.id == category_id,
        TreatmentCategoryModel.user_id == current_user.id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    for key, value in updated_data.dict(exclude_unset=True).items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category

# 카테고리 삭제
@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    category = db.query(TreatmentCategoryModel).filter(
        TreatmentCategoryModel.id == category_id,
        TreatmentCategoryModel.user_id == current_user.id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.treatments:
        raise HTTPException(status_code=400, detail="해당 카테고리에 속한 시술이 있어 삭제할 수 없습니다.")
    
    db.delete(category)
    db.commit()