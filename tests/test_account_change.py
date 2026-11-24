"""
계정 변경 API 테스트 (티켓 19b).

- POST /users/me/password: 현재 비밀번호 확인 후 비밀번호 변경
- POST /users/me/email: 현재 비밀번호 확인 후 이메일(아이디) 변경, 중복 409
- PUT /users/me: 이메일·비밀번호는 더 이상 바뀌지 않음 (구버전 앱 요청도 200)
"""
from typing import Dict

import bcrypt
import pytest

from models.user import User
from tests.conftest import signup_body

EMAIL_A = "owner-a@example.com"
EMAIL_B = "owner-b@example.com"
PW_A = "passwordA1"
PW_B = "passwordB2"
NEW_PW = "newpass456"
WRONG_CURRENT = "현재 비밀번호가 올바르지 않습니다."


def signup(client, email: str, password: str) -> Dict[str, str]:
    r = client.post("/auth/signup", json=signup_body("원장", email, password))
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer {}".format(r.json()["access_token"])}


def signin(client, email: str, password: str):
    return client.post("/auth/signin", data={"username": email, "password": password})


def stored(db_session, email: str) -> User:
    db_session.expire_all()
    return db_session.query(User).filter(User.email == email).first()


@pytest.fixture
def headers_a(client) -> Dict[str, str]:
    return signup(client, EMAIL_A, PW_A)


@pytest.fixture
def headers_b(client) -> Dict[str, str]:
    return signup(client, EMAIL_B, PW_B)


# ---------------- POST /users/me/password ----------------

def test_change_password_success(client, db_session, headers_a):
    r = client.post("/users/me/password", json={"current_password": PW_A, "new_password": NEW_PW}, headers=headers_a)

    assert r.status_code == 200, r.text
    assert r.json() == {"message": "비밀번호가 변경되었습니다."}
    assert stored(db_session, EMAIL_A).password.startswith("$argon2id$")
    assert signin(client, EMAIL_A, NEW_PW).status_code == 200
    assert signin(client, EMAIL_A, PW_A).status_code == 401


def test_change_password_wrong_current_password_is_400(client, db_session, headers_a):
    original = stored(db_session, EMAIL_A).password

    r = client.post("/users/me/password", json={"current_password": "wrongpass1", "new_password": NEW_PW}, headers=headers_a)

    assert r.status_code == 400, r.text
    assert r.json() == {"detail": WRONG_CURRENT}
    assert stored(db_session, EMAIL_A).password == original
    assert signin(client, EMAIL_A, PW_A).status_code == 200


@pytest.mark.parametrize("new_password", ["short1a", "abcdefgh", "12345678", "a1" + "b" * 63])
def test_change_password_rule_violation_is_422(client, db_session, headers_a, new_password):
    original = stored(db_session, EMAIL_A).password

    r = client.post("/users/me/password", json={"current_password": PW_A, "new_password": new_password}, headers=headers_a)

    assert r.status_code == 422, r.text
    assert stored(db_session, EMAIL_A).password == original


def test_change_password_same_as_current_is_422_on_new_password(client, db_session, headers_a):
    original = stored(db_session, EMAIL_A).password

    r = client.post("/users/me/password", json={"current_password": PW_A, "new_password": PW_A}, headers=headers_a)

    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert isinstance(detail, list) and detail[0]["loc"] == ["body", "new_password"]
    assert stored(db_session, EMAIL_A).password == original


def test_change_password_wrong_current_takes_precedence_over_same_password(client, headers_a):
    # 현재 비밀번호가 틀리면 "같은 비밀번호" 여부와 상관없이 400
    r = client.post(
        "/users/me/password", json={"current_password": "wrongpass1", "new_password": "wrongpass1"}, headers=headers_a
    )

    assert r.status_code == 400, r.text


@pytest.mark.parametrize("body", [{"new_password": NEW_PW}, {"current_password": PW_A}, {}])
def test_change_password_missing_field_is_422(client, headers_a, body):
    assert client.post("/users/me/password", json=body, headers=headers_a).status_code == 422


def test_change_password_requires_token(client, headers_a):
    r = client.post("/users/me/password", json={"current_password": PW_A, "new_password": NEW_PW})

    assert r.status_code == 401


def test_change_password_from_legacy_bcrypt_account(client, db_session):
    # 16b 이전 bcrypt 계정(규칙 이전의 약한 비밀번호)도 현재 비밀번호 확인이 되고, 새 비밀번호는 Argon2id
    legacy_hash = bcrypt.hashpw(b"1234", bcrypt.gensalt(12)).decode("utf-8")
    db_session.add(User(email=EMAIL_A, name="기존원장", password=legacy_hash))
    db_session.commit()
    token = signin(client, EMAIL_A, "1234").json()["access_token"]

    r = client.post(
        "/users/me/password",
        json={"current_password": "1234", "new_password": NEW_PW},
        headers={"Authorization": "Bearer {}".format(token)},
    )

    assert r.status_code == 200, r.text
    assert stored(db_session, EMAIL_A).password.startswith("$argon2id$")
    assert signin(client, EMAIL_A, NEW_PW).status_code == 200
    assert signin(client, EMAIL_A, "1234").status_code == 401


def test_change_password_does_not_touch_other_account(client, db_session, headers_a, headers_b):
    b_hash = stored(db_session, EMAIL_B).password

    r = client.post("/users/me/password", json={"current_password": PW_A, "new_password": NEW_PW}, headers=headers_a)

    assert r.status_code == 200, r.text
    assert stored(db_session, EMAIL_B).password == b_hash
    assert signin(client, EMAIL_B, PW_B).status_code == 200


# ---------------- POST /users/me/email ----------------

def test_change_email_success(client, db_session, headers_a):
    r = client.post("/users/me/email", json={"current_password": PW_A, "new_email": "renamed@example.com"}, headers=headers_a)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "renamed@example.com"
    assert "password" not in body
    assert signin(client, "renamed@example.com", PW_A).status_code == 200
    assert signin(client, EMAIL_A, PW_A).status_code == 401
    assert stored(db_session, EMAIL_A) is None

    # 같은 토큰(사용자 id 기준)으로 계속 인증된다
    me = client.get("/users/me", headers=headers_a)
    assert me.status_code == 200 and me.json()["email"] == "renamed@example.com"


def test_change_email_wrong_current_password_is_400(client, db_session, headers_a):
    r = client.post("/users/me/email", json={"current_password": "wrongpass1", "new_email": "renamed@example.com"}, headers=headers_a)

    assert r.status_code == 400, r.text
    assert r.json() == {"detail": WRONG_CURRENT}
    assert stored(db_session, EMAIL_A) is not None


def test_change_email_taken_by_other_account_is_409(client, db_session, headers_a, headers_b):
    r = client.post("/users/me/email", json={"current_password": PW_A, "new_email": EMAIL_B}, headers=headers_a)

    assert r.status_code == 409, r.text
    assert stored(db_session, EMAIL_A) is not None
    assert signin(client, EMAIL_B, PW_B).status_code == 200  # B 계정은 그대로


def test_change_email_wrong_password_and_taken_email_is_400_not_409(client, headers_a, headers_b):
    # 현재 비밀번호 확인이 먼저: 비밀번호를 모르면 "그 이메일이 가입돼 있는지"를 알 수 없어야 함
    r = client.post("/users/me/email", json={"current_password": "wrongpass1", "new_email": EMAIL_B}, headers=headers_a)

    assert r.status_code == 400, r.text


@pytest.mark.parametrize("new_email", ["not-an-email", "a@", "@example.com", ""])
def test_change_email_invalid_format_is_422(client, db_session, headers_a, new_email):
    r = client.post("/users/me/email", json={"current_password": PW_A, "new_email": new_email}, headers=headers_a)

    assert r.status_code == 422, r.text
    assert stored(db_session, EMAIL_A) is not None


def test_change_email_same_as_current_is_400(client, headers_a):
    r = client.post("/users/me/email", json={"current_password": PW_A, "new_email": EMAIL_A}, headers=headers_a)

    assert r.status_code == 400, r.text


def test_change_email_requires_token(client, headers_a):
    r = client.post("/users/me/email", json={"current_password": PW_A, "new_email": "renamed@example.com"})

    assert r.status_code == 401


# ---------------- PUT /users/me (구버전 앱 호환) ----------------

def test_put_me_old_app_payload_still_200_and_keeps_email_and_password(client, db_session, headers_a):
    # 구버전 프론트 registerUserInfo: email(현재 값)과 password(보통 undefined → JSON에서 빠지거나 null)를 같이 보냄
    original_hash = stored(db_session, EMAIL_A).password
    payloads = [
        {"name": "새이름", "email": EMAIL_A, "store_name": "곱슬 미용실", "address": "서울", "address_detail": "1층", "zip_code": "01234"},
        {"name": "새이름2", "email": EMAIL_A, "password": None, "store_name": "곱슬 미용실2"},
        {"name": "새이름3", "email": EMAIL_A, "password": "hackedpass1", "store_name": "곱슬 미용실3"},
    ]

    for payload in payloads:
        r = client.put("/users/me", json=payload, headers=headers_a)

        assert r.status_code == 200, r.text
        assert r.json()["name"] == payload["name"]
        assert r.json()["store_name"] == payload["store_name"]
        assert r.json()["email"] == EMAIL_A
        assert "password" not in r.json()

    user = stored(db_session, EMAIL_A)
    assert user.password == original_hash
    assert user.address == "서울" and user.zip_code == "01234"
    assert signin(client, EMAIL_A, PW_A).status_code == 200
    assert signin(client, EMAIL_A, "hackedpass1").status_code == 401


def test_put_me_with_different_email_does_not_change_email(client, db_session, headers_a):
    r = client.put("/users/me", json={"name": "원장", "email": "other@example.com"}, headers=headers_a)

    assert r.status_code == 200, r.text
    assert r.json()["email"] == EMAIL_A
    assert stored(db_session, EMAIL_A) is not None
    assert stored(db_session, "other@example.com") is None


def test_put_me_with_other_accounts_email_is_200_not_500(client, db_session, headers_a, headers_b):
    # 기존에는 unique 제약 위반으로 500이었다 (KI-11)
    r = client.put("/users/me", json={"name": "원장", "email": EMAIL_B}, headers=headers_a)

    assert r.status_code == 200, r.text
    assert r.json()["email"] == EMAIL_A


def test_change_email_unique_violation_race_is_409_not_500(client, db_session, headers_a, headers_b):
    """중복 확인을 통과한 직후 다른 요청이 같은 이메일을 먼저 저장한 경우 (DB unique 제약 → 409)."""
    from sqlalchemy.orm import Session

    from database.session import engine, get_db
    from main import app

    class _MissDuplicateCheck:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None  # 중복 확인이 "없음"으로 보이게 해서 경쟁 상황을 재현

    class RaceSession(Session):
        def query(self, *entities, **kwargs):
            if len(entities) == 1 and entities[0] is User.id:
                return _MissDuplicateCheck()
            return super().query(*entities, **kwargs)

    def _race_db():
        db = RaceSession(bind=engine, autoflush=False, autocommit=False)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _race_db

    r = client.post("/users/me/email", json={"current_password": PW_A, "new_email": EMAIL_B}, headers=headers_a)

    assert r.status_code == 409, r.text
    assert stored(db_session, EMAIL_A) is not None
