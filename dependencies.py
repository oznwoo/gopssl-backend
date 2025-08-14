from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from core.security import decode_access_token
from database.session import get_db
from models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/signin")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    print(f"🔍 토큰 검증 시작: {token[:20]}...")  # 디버깅용 로그
    
    payload = decode_access_token(token)
    print(f"🔍 토큰 디코딩 결과: {payload}")  # 디버깅용 로그
    
    if not payload:
        print("❌ 토큰 디코딩 실패")  # 디버깅용 로그
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 유효하지 않거나 만료되었습니다.",
        )

    user_id = payload.get("sub")
    print(f"🔍 추출된 user_id: {user_id}")  # 디버깅용 로그
    
    if user_id is None:
        raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다.")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자가 존재하지 않습니다.")

    print(f"✅ 사용자 인증 성공: {user.email}")  # 디버깅용 로그
    return user