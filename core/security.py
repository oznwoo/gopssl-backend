from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Argon2id 파라미터: OWASP 권장 최소 구성 (m=19 MiB, t=2, p=1).
# 운영 서버 RAM(1GB)을 고려해 이 이상 올리지 않는다.
ARGON2_TIME_COST = 2
ARGON2_MEMORY_COST_KIB = 19456
ARGON2_PARALLELISM = 1

# 첫 번째 해셔(Argon2id)로 새 해시를 만들고, bcrypt는 기존 해시 검증용으로만 쓴다.
password_hash = PasswordHash(
    (
        Argon2Hasher(
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST_KIB,
            parallelism=ARGON2_PARALLELISM,
        ),
        BcryptHasher(),
    )
)


# 비밀번호 해싱 (Argon2id)
def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    valid, _ = verify_and_update_password(plain, hashed)
    return valid


def verify_and_update_password(plain: str, hashed: str) -> Tuple[bool, Optional[str]]:
    """
    비밀번호를 검증하고, 저장된 해시를 바꿔야 하면 새 해시를 함께 돌려준다.

    - (False, None): 비밀번호 불일치 또는 알 수 없는 해시 형식
    - (True, None): 일치, 갱신 불필요
    - (True, new_hash): 일치, bcrypt 등 옛 해시라 Argon2id 새 해시로 바꿔 저장해야 함
    """
    try:
        return password_hash.verify_and_update(plain, hashed)
    except (UnknownHashError, ValueError):
        # 지원하지 않는 해시 형식(UnknownHashError)이나 손상된 bcrypt 해시(ValueError)는 로그인 실패로 처리
        return False, None

# JWT 생성
def create_access_token(data: Dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire_dt = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # exp를 Unix 타임스탬프(정수)로 저장하여 역직렬화 차이를 방지
    to_encode.update({"exp": int(expire_dt.timestamp())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# JWT 검증
def decode_access_token(token: str) -> Optional[Dict]:
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