"""
회원가입 정책 테스트 (티켓 16b).

- 비밀번호 규칙: 8~64자, 영문·숫자 각각 1개 이상 (가입·PUT /users/me) → 위반 시 422
- 약관·처리방침·만 14세 동의: 셋 다 true 여야 가입, 동의 시각·버전 저장
- 해시: 새 해시는 Argon2id, 기존 bcrypt 해시는 로그인 성공 시 Argon2id 로 전환
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from pwdlib.hashers.argon2 import Argon2Hasher

from models.user import User
from tests.conftest import signup_body

EMAIL = "owner@example.com"
GOOD_PASSWORD = "goodpass123"


def signin(client, email: str, password: str):
    return client.post("/auth/signin", data={"username": email, "password": password})


def stored_user(db_session, email: str = EMAIL) -> User:
    db_session.expire_all()
    return db_session.query(User).filter(User.email == email).first()


def create_legacy_user(db_session, password: str, prefix: bytes = b"2b") -> str:
    """passlib(bcrypt) 시절에 가입한 계정을 흉내 낸다."""
    legacy_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12, prefix)).decode("utf-8")
    db_session.add(User(email=EMAIL, name="기존원장", password=legacy_hash))
    db_session.commit()
    return legacy_hash


# ---------------- 비밀번호 규칙 (가입) ----------------

@pytest.mark.parametrize(
    "password",
    [
        "short1a",            # 7자
        "abcdefgh",           # 숫자 없음
        "12345678",           # 영문 없음
        "a1" + "b" * 63,      # 65자
        "비밀번호12345",       # 영문 없음 (한글+숫자)
        "",                   # 빈 값
    ],
)
def test_signup_rejects_password_breaking_rule(client, db_session, password):
    r = client.post("/auth/signup", json=signup_body("원장", EMAIL, password))

    assert r.status_code == 422, r.text
    assert stored_user(db_session) is None


@pytest.mark.parametrize("password", ["abcdefg1", "a1" + "b" * 62, "Pass word 1!"])
def test_signup_accepts_password_within_rule(client, db_session, password):
    r = client.post("/auth/signup", json=signup_body("원장", EMAIL, password))

    assert r.status_code == 200, r.text
    assert signin(client, EMAIL, password).status_code == 200


# ---------------- 동의 ----------------

@pytest.mark.parametrize("field", ["agree_terms", "agree_privacy", "agree_over_14"])
def test_signup_rejects_when_any_consent_is_false(client, db_session, field):
    r = client.post("/auth/signup", json=signup_body("원장", EMAIL, GOOD_PASSWORD, **{field: False}))

    assert r.status_code == 422, r.text
    assert stored_user(db_session) is None


@pytest.mark.parametrize(
    "field", ["agree_terms", "agree_privacy", "agree_over_14", "terms_version", "privacy_version"]
)
def test_signup_rejects_when_consent_field_missing(client, db_session, field):
    body = signup_body("원장", EMAIL, GOOD_PASSWORD)
    del body[field]

    r = client.post("/auth/signup", json=body)

    assert r.status_code == 422, r.text
    assert stored_user(db_session) is None


@pytest.mark.parametrize("field", ["terms_version", "privacy_version"])
def test_signup_rejects_empty_version(client, db_session, field):
    r = client.post("/auth/signup", json=signup_body("원장", EMAIL, GOOD_PASSWORD, **{field: ""}))

    assert r.status_code == 422, r.text
    assert stored_user(db_session) is None


def test_signup_stores_argon2id_hash_and_consent(client, db_session):
    before = datetime.now(timezone.utc)

    r = client.post(
        "/auth/signup",
        json=signup_body("원장", EMAIL, GOOD_PASSWORD, terms_version="t-v1", privacy_version="p-v2"),
    )

    assert r.status_code == 200, r.text
    assert set(r.json().keys()) == {"access_token", "token_type"}

    user = stored_user(db_session)
    assert user.password.startswith("$argon2id$")
    assert "m=19456,t=2,p=1" in user.password
    assert GOOD_PASSWORD not in user.password
    assert user.terms_version == "t-v1"
    assert user.privacy_version == "p-v2"
    assert user.agreed_at is not None
    assert before - timedelta(seconds=5) <= user.agreed_at <= datetime.now(timezone.utc) + timedelta(seconds=5)


# ---------------- 로그인 & 해시 전환 ----------------

@pytest.mark.parametrize("prefix", [b"2b", b"2a"])
def test_legacy_bcrypt_login_succeeds_and_migrates_to_argon2id(client, db_session, prefix):
    # 기존 계정은 규칙 도입 전 비밀번호(짧거나 숫자만)일 수 있다 → 로그인은 그대로 되어야 함
    legacy_password = "1234"
    legacy_hash = create_legacy_user(db_session, legacy_password, prefix)
    assert legacy_hash.startswith("$" + prefix.decode() + "$")

    r = signin(client, EMAIL, legacy_password)

    assert r.status_code == 200, r.text
    migrated = stored_user(db_session).password
    assert migrated.startswith("$argon2id$")
    assert migrated != legacy_hash

    # 받은 토큰으로 인증 요청이 되는지
    me = client.get("/users/me", headers={"Authorization": "Bearer {}".format(r.json()["access_token"])})
    assert me.status_code == 200, me.text

    # 전환 후에도 같은 비밀번호로 로그인되고, 해시는 다시 바뀌지 않음
    assert signin(client, EMAIL, legacy_password).status_code == 200
    assert stored_user(db_session).password == migrated


def test_wrong_password_returns_401_and_keeps_legacy_hash(client, db_session):
    legacy_hash = create_legacy_user(db_session, "rightpass1")

    r = signin(client, EMAIL, "wrongpass1")

    assert r.status_code == 401, r.text
    assert stored_user(db_session).password == legacy_hash


def test_wrong_password_returns_401_and_keeps_argon2_hash(client, db_session):
    assert client.post("/auth/signup", json=signup_body("원장", EMAIL, GOOD_PASSWORD)).status_code == 200
    original = stored_user(db_session).password

    r = signin(client, EMAIL, "wrongpass1")

    assert r.status_code == 401, r.text
    assert stored_user(db_session).password == original


def test_unknown_email_returns_401(client):
    assert signin(client, "nobody@example.com", GOOD_PASSWORD).status_code == 401


def test_unrecognized_stored_hash_returns_401_not_500(client, db_session):
    db_session.add(User(email=EMAIL, name="손상", password="not-a-real-hash"))
    db_session.commit()

    assert signin(client, EMAIL, GOOD_PASSWORD).status_code == 401


def test_argon2_hash_with_old_params_is_rehashed_on_login(client, db_session):
    old_hash = Argon2Hasher(time_cost=3, memory_cost=65536, parallelism=4).hash(GOOD_PASSWORD)
    db_session.add(User(email=EMAIL, name="원장", password=old_hash))
    db_session.commit()

    assert signin(client, EMAIL, GOOD_PASSWORD).status_code == 200

    new_hash = stored_user(db_session).password
    assert new_hash != old_hash
    assert "m=19456,t=2,p=1" in new_hash


# ---------------- PUT /users/me ----------------

def _signup_and_token(client) -> str:
    r = client.post("/auth/signup", json=signup_body("원장", EMAIL, GOOD_PASSWORD))
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.parametrize("password", ["short1a", "abcdefgh", "12345678", "a1" + "b" * 63])
def test_update_me_rejects_password_breaking_rule(client, db_session, password):
    token = _signup_and_token(client)
    original = stored_user(db_session).password

    r = client.put("/users/me", json={"password": password}, headers={"Authorization": "Bearer {}".format(token)})

    assert r.status_code == 422, r.text
    assert stored_user(db_session).password == original


def test_update_me_with_valid_password_stores_argon2id(client, db_session):
    token = _signup_and_token(client)

    r = client.put("/users/me", json={"password": "newpass456"}, headers={"Authorization": "Bearer {}".format(token)})

    assert r.status_code == 200, r.text
    assert stored_user(db_session).password.startswith("$argon2id$")
    assert signin(client, EMAIL, "newpass456").status_code == 200
    assert signin(client, EMAIL, GOOD_PASSWORD).status_code == 401


def test_update_me_without_password_keeps_hash(client, db_session):
    token = _signup_and_token(client)
    original = stored_user(db_session).password

    r = client.put("/users/me", json={"store_name": "곱슬 미용실"}, headers={"Authorization": "Bearer {}".format(token)})

    assert r.status_code == 200, r.text
    assert stored_user(db_session).password == original


# ---------------- 응답에 비밀번호·해시가 섞이지 않음 ----------------

def test_user_responses_do_not_expose_password_or_hash(client, db_session):
    token = _signup_and_token(client)
    headers = {"Authorization": "Bearer {}".format(token)}
    stored_hash = stored_user(db_session).password

    me = client.get("/users/me", headers=headers)
    updated = client.put("/users/me", json={"name": "새이름"}, headers=headers)

    for r in (me, updated):
        assert r.status_code == 200, r.text
        assert "password" not in r.json()
        assert stored_hash not in r.text
        assert "$argon2id$" not in r.text
