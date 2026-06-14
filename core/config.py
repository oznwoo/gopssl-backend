import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
SECRET_KEY: str = os.getenv("SECRET_KEY", "")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
KAKAO_REST_API_KEY: str = os.getenv("KAKAO_REST_API_KEY", "")
ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

_required = {
    "DATABASE_URL": DATABASE_URL,
    "SECRET_KEY": SECRET_KEY,
}
_missing = [k for k, v in _required.items() if not v]
if _missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(_missing)}")
