from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserRead
from models.user import User
from core.security import hash_password, create_access_token
from database.session import SessionLocal, get_db
from dependencies import get_current_user
from datetime import timedelta

router = APIRouter(prefix="/users", tags=["users"])

# Read(전체)
@router.get("/", response_model=UserRead)
def get_user(db: Session = Depends(get_db)):
  return db.query(User).all()

# Read(본인)
@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Read(개별)
@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
  user = db.query(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=404, detail="사용자를 찾읗 수 없습니다.")
  return user

# Update
@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: int, updated_data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    for key, value in updated_data.dict(exclude_unset=True).items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user

# Delete
@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    db.delete(user)
    db.commit()
    return {"message": "사용자가 삭제되었습니다."}