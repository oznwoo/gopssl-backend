from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserRead, UserUpdate
from models.user import User
from core.security import hash_password, create_access_token
from database.session import SessionLocal, get_db
from dependencies import get_current_user
from datetime import timedelta

router = APIRouter(prefix="/users", tags=["users"])

# Read(전체) - 보안상 제거 (모든 사용자 정보를 볼 수 없음)
# @router.get("/", response_model=UserRead)
# def get_user(db: Session = Depends(get_db)):
#   return db.query(User).all()

# Read(본인)
@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Read(개별) - 보안상 제거 (다른 사용자 정보를 볼 수 없음)
# @router.get("/{user_id}", response_model=UserRead)
# def read_user(user_id: int, db: Session = Depends(get_db)):
#   user = db.query(User.id == user_id).first()
#   if not user:
#     raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
#   return user

# Update - 본인만 수정 가능
@router.put("/me", response_model=UserRead)
def update_me(updated_data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 비밀번호가 포함된 경우 해싱
    if updated_data.password:
        current_user.password = hash_password(updated_data.password)
    
    # 다른 필드들 업데이트 (None이 아닌 값만)
    update_data = updated_data.dict(exclude_unset=True, exclude={'password'})
    for key, value in update_data.items():
        if value is not None:
            setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)
    return current_user

# Delete - 본인만 삭제 가능
@router.delete("/me")
def delete_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.delete(current_user)
    db.commit()
    return {"message": "사용자 계정이 삭제되었습니다."}