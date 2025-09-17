import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from datetime import datetime, timedelta
from typing import Optional

# 비밀번호 해싱용
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24시간 (24 * 60)

# 비밀번호 해싱
def hash_password(password: str) -> str:
  return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
  return pwd_context.verify(plain, hashed)

# JWT 생성
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire_dt = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # exp를 Unix 타임스탬프(정수)로 저장하여 역직렬화 차이를 방지
    to_encode.update({"exp": int(expire_dt.timestamp())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# JWT 검증
def decode_access_token(token: str) -> Optional[dict]:
    try:
        
        # 만료 검증은 jose가 수행
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True}
        )
        return payload
    except ExpiredSignatureError as e:
        print(f"❌ JWT 만료 에러: {e}")  # 디버깅용 로그
        return None
    except JWTError as e:
        print(f"❌ JWT 에러: {e}")  # 디버깅용 로그
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 에러: {e}")  # 디버깅용 로그
        return None