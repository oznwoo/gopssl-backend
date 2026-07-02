from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate
from database.session import get_db
from core.security import verify_password, create_access_token, hash_password, decode_access_token
from schemas.user import Token
from dependencies import get_current_user
from datetime import timedelta
from typing import Optional

router = APIRouter(prefix="/auth", tags=["auth"])

# Create
@router.post("/signup", response_model=Token)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
  # 이메일 중복 체크
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
        expires_delta=timedelta(hours=24)  # 24시간으로 통일
  )

  return {"access_token": token, "token_type": "bearer"}

@router.post("/signin", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="잘못된 이메일 또는 비밀번호")
    
    # 로그인 성공 시 새 토큰 발급 (24시간으로 늘림)
    token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(hours=24)  # 24시간으로 설정
    )
    return {"access_token": token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user)):
    """토큰 갱신 엔드포인트 - 현재 유효한 토큰으로 새 토큰 발급"""
    # 현재 사용자 정보로 새 토큰 발급
    new_token = create_access_token(
        data={"sub": str(current_user.id)},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": new_token, "token_type": "bearer"}

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """로그아웃 엔드포인트 - 클라이언트에서 토큰 삭제하도록 안내"""
    return {"message": "로그아웃되었습니다. 클라이언트에서 토큰을 삭제해주세요."}