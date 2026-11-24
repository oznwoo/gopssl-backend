import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

# 비밀번호 규칙 (프론트 16a와 동일): 8~64자, 영문·숫자 각각 1개 이상
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64
_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"[0-9]")


def validate_password_rule(password: str) -> str:
  if not (PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH):
    raise ValueError(
      "비밀번호는 {}자 이상 {}자 이하여야 합니다.".format(PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH)
    )
  if not _HAS_LETTER.search(password) or not _HAS_DIGIT.search(password):
    raise ValueError("비밀번호는 영문과 숫자를 각각 1개 이상 포함해야 합니다.")
  return password


# 회원가입 요청용 (입력 스키마)
class UserCreate(BaseModel):
  name: str
  email: EmailStr
  password: str
  store_name: Optional[str] = None
  address: Optional[str] = None
  address_detail: Optional[str] = None
  zip_code: Optional[str] = None

  # 약관·개인정보 처리방침 동의 (만 14세 이상 확인 포함). 셋 다 true여야 가입 가능
  terms_version: str = Field(min_length=1, max_length=50)
  privacy_version: str = Field(min_length=1, max_length=50)
  agree_terms: bool
  agree_privacy: bool
  agree_over_14: bool

  @field_validator("password")
  @classmethod
  def _check_password(cls, v: str) -> str:
    return validate_password_rule(v)

  @field_validator("agree_terms", "agree_privacy", "agree_over_14")
  @classmethod
  def _must_agree(cls, v: bool) -> bool:
    if v is not True:
      raise ValueError("필수 동의 항목에 모두 동의해야 합니다.")
    return v


class UserUpdate(BaseModel):
  name: Optional[str] = None
  email: Optional[EmailStr] = None
  password: Optional[str] = None
  store_name: Optional[str] = None
  address: Optional[str] = None
  address_detail: Optional[str] = None
  zip_code: Optional[str] = None

  @field_validator("password")
  @classmethod
  def _check_password(cls, v: Optional[str]) -> Optional[str]:
    if v is None:
      return v
    return validate_password_rule(v)

# 유저 조회 응답용 (출력 스키마)
class UserRead(BaseModel):
  id: int
  name: Optional[str]
  email: EmailStr
  store_name: Optional[str] = None
  address: Optional[str] = None
  address_detail: Optional[str] = None
  zip_code: Optional[str] = None
  created_at: datetime

  class Config: 
    from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
  