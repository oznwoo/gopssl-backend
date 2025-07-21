from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate
from database.session import get_db
from core.security import verify_password, create_access_token, hash_password
from schemas.user import Token
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

# Create
@router.post("/signup", response_model=Token)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
  # 이메일 중복 체크
  print(user)
  existing_user = db.query(User).filter(User.email == user.email).first()
  if existing_user:
    raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")
  
  new_user = User(
     email=user.email,
     name=user.name,
     password=hash_password(user.password)
  )
  db.add(new_user)
  db.commit()
  db.refresh(new_user)

  # 회원가입 후 access_token 발급
  token = create_access_token(
        data={"sub": str(new_user.id)},
        expires_delta=timedelta(minutes=30)
  )

  return {"access_token": token, "token_type": "bearer"}

@router.post("/signin", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="잘못된 이메일 또는 비밀번호")
    
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}