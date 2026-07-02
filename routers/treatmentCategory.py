from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict

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
    ).order_by(TreatmentCategoryModel.display_order).all()

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
    # display_order 계산: 현재 사용자의 카테고리 개수 + 1
    new_order = db.query(TreatmentCategoryModel).filter(
        TreatmentCategoryModel.user_id == current_user.id
    ).count() + 1

    db_category = TreatmentCategoryModel(
        **category.dict(), 
        user_id=current_user.id,
        display_order=new_order
    )

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
    
    deleted_order = category.display_order

    db.delete(category)
    db.commit()

    # 삭제된 카테고리보다 순서가 뒤에 있는 카테고리들의 display_order를 1씩 감소
    db.query(TreatmentCategoryModel).filter(
        TreatmentCategoryModel.user_id == current_user.id,
        TreatmentCategoryModel.display_order > deleted_order
    ).update({"display_order": TreatmentCategoryModel.display_order - 1}, synchronize_session=False)
    db.commit()

@router.post("/reorder", status_code=status.HTTP_200_OK)
def reorder_categories(
    order_data: Dict[int, int], # {category_id: new_order}
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """카테고리 순서를 업데이트합니다."""    
    for category_id, new_order in order_data.items():
        category = db.query(TreatmentCategoryModel).filter(
            TreatmentCategoryModel.id == category_id,
            TreatmentCategoryModel.user_id == current_user.id
        ).first()
        if category:
            category.display_order = new_order
        else:
            # 여기서 에러가 발생하면 get_db 의존성에서 자동으로 rollback 처리합니다.
            raise HTTPException(status_code=404, detail=f"Category with id {category_id} not found or not owned by user.")
            
    db.commit() # 모든 변경이 끝난 후 commit을 직접 호출합니다.
    
    return {"message": "Categories reordered successfully"}
