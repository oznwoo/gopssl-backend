from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserRead, UserUpdate, PasswordChange, EmailChange
from models.user import User
from core.security import hash_password, create_access_token, verify_and_update_password
from database.session import SessionLocal, get_db
from dependencies import get_current_user
from datetime import timedelta

router = APIRouter(prefix="/users", tags=["users"])

# Read(전체) - 보안상 제거 (모든 사용자 정보를 볼 수 없음)
# @router.get("/", response_model=UserRead)
# def get_user(db: Session = Depends(get_db)):
#   return db.query(User).all()

# Read(본인)
@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Read(개별) - 보안상 제거 (다른 사용자 정보를 볼 수 없음)
# @router.get("/{user_id}", response_model=UserRead)
# def read_user(user_id: int, db: Session = Depends(get_db)):
#   user = db.query(User.id == user_id).first()
#   if not user:
#     raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
#   return user

# Update - 본인만 수정 가능
@router.put("/me", response_model=UserRead)
def update_me(updated_data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 이메일·비밀번호는 UserUpdate에 없으므로 여기서는 바뀌지 않는다 (전용 API 사용)
    # 다른 필드들 업데이트 (None이 아닌 값만)
    update_data = updated_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)
    return current_user

# 현재 비밀번호가 틀렸을 때의 응답.
# 401이 아니라 400을 쓴다: 앱의 axios 인터셉터가 401을 "토큰 만료"로 보고 토큰 갱신·재시도·로그아웃을 하기 때문에
# 401로 주면 "현재 비밀번호가 틀렸어요"를 구분해 보여줄 수 없다.
WRONG_CURRENT_PASSWORD = "현재 비밀번호가 올바르지 않습니다."


def _verify_current_password_or_400(user: User, current_password: str) -> None:
    valid, updated_hash = verify_and_update_password(current_password, user.password)
    if not valid:
        raise HTTPException(status_code=400, detail=WRONG_CURRENT_PASSWORD)
    # 기존 bcrypt 해시면 로그인과 같은 방식으로 Argon2id로 바꿔 둔다 (커밋은 호출한 쪽에서)
    if updated_hash:
        user.password = updated_hash


# 비밀번호 변경 - 현재 비밀번호 확인 후에만
@router.post("/me/password", response_model=dict)
def change_password(body: PasswordChange, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_current_password_or_400(current_user, body.current_password)

    # 현재 비밀번호가 맞다는 것이 확인됐으므로 문자열 비교로 "같은 비밀번호"를 판단할 수 있다.
    # 규칙 위반(스키마 422)과 같은 형식으로 new_password 필드 오류를 돌려준다.
    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=422,
            detail=[{
                "type": "value_error",
                "loc": ["body", "new_password"],
                "msg": "새 비밀번호가 현재 비밀번호와 같습니다.",
                "input": None,
            }],
        )

    current_user.password = hash_password(body.new_password)
    db.commit()
    # 한계: 기존에 발급된 토큰은 만료(24시간)까지 계속 유효하다 (토큰 무효화는 후속)
    return {"message": "비밀번호가 변경되었습니다."}


# 이메일(아이디) 변경 - 현재 비밀번호 확인 후에만
@router.post("/me/email", response_model=UserRead)
def change_email(body: EmailChange, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_current_password_or_400(current_user, body.current_password)

    new_email = body.new_email
    if new_email == current_user.email:
        raise HTTPException(status_code=400, detail="현재 이메일과 같습니다.")

    # 가입·로그인과 같은 기준(정확히 일치)으로 중복 확인
    taken = db.query(User.id).filter(User.email == new_email, User.id != current_user.id).first()
    if taken:
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.")

    current_user.email = new_email
    try:
        db.commit()
    except IntegrityError:
        # 중복 확인과 저장 사이에 같은 이메일이 먼저 저장된 경우 (unique 제약) → 500 대신 409
        db.rollback()
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.")
    db.refresh(current_user)
    return current_user


# Delete - 본인만 삭제 가능
@router.delete("/me")
def delete_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.delete(current_user)
    db.commit()
    return {"message": "사용자 계정이 삭제되었습니다."}