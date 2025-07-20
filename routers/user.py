from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserRead
from models.user import User
from database.session import SessionLocal, get_db

router = APIRouter(prefix="/users", tags=["users"])

# Create
@router.post("/", response_model=UserRead)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
  # 이메일 중복 체크
  existing_user = db.query(User).filter(User.email == user.email).first()
  if existing_user:
    raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")
  
  new_user = User(**user.dict())
  db.add(new_user)
  db.commit()
  db.refresh(new_user)
  return new_user

# Read(전체)
@router.get("/", response_model=UserRead)
def get_user(db: Session = Depends(get_db)):
  return db.query(User).all()

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