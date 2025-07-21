import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

# 비밀번호 해싱용
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 비밀번호 해싱
def hash_password(password: str) -> str:
  return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
  return pwd_context.verify(plain, hashed)

# JWT 생성
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# JWT 검증
def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 토큰 만료 시간 확인 (선택)
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            return None
        return payload
    except JWTError:
        return None