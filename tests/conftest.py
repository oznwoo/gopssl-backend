"""
테스트 공통 설정.

- 앱을 import 하기 전에 DATABASE_URL 을 로컬 테스트 DB 로 강제 지정한다.
  (core.config 의 load_dotenv() 는 이미 설정된 환경변수를 덮어쓰지 않으므로 .env 값이 끼어들지 않는다)
- 매 테스트마다 drop_all → create_all 을 실행하므로, 로컬 *_test DB 가 아니면 즉시 중단한다.
"""
import os
from typing import Dict, Iterator
from urllib.parse import urlparse

import pytest

TEST_DATABASE_URL = "postgresql+psycopg2://gopssl:gopssl@localhost:5432/gopssl_test"
ALLOWED_HOSTS = ("localhost", "127.0.0.1")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"


def _abort_if_unsafe(host, database) -> None:
    if host not in ALLOWED_HOSTS or not (database or "").endswith("_test"):
        pytest.exit(
            "테스트 DB 안전장치: 로컬(localhost/127.0.0.1)의 *_test DB 가 아니므로 중단합니다.",
            returncode=1,
        )


# 1차: 앱 import 전 (main.py 는 import 시점에 create_all 로 DB 에 접속한다)
_parsed = urlparse(os.environ["DATABASE_URL"])
_abort_if_unsafe(_parsed.hostname, _parsed.path.lstrip("/"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from database.session import Base, engine, get_db  # noqa: E402

# 2차: 실제로 만들어진 엔진 기준으로 한 번 더 확인
_abort_if_unsafe(engine.url.host, engine.url.database)

from main import app  # noqa: E402

TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _override_get_db() -> Iterator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _reset_db() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session() -> Iterator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------- 헬퍼 ----------------

class Shop:
    """가게(원장님 계정) 1개 + 고객 1명 + 시술 1개."""

    def __init__(self, token: str, user_id: int, category_id: int, customer_id: int, treatment_id: int):
        self.token = token
        self.user_id = user_id
        self.category_id = category_id
        self.customer_id = customer_id
        self.treatment_id = treatment_id

    @property
    def headers(self) -> Dict[str, str]:
        return {"Authorization": "Bearer {}".format(self.token)}


def add_customer(client: TestClient, token: str, user_id: int, name: str) -> int:
    r = client.post(
        "/customers/",
        json={"user_id": user_id, "name": name},
        headers={"Authorization": "Bearer {}".format(token)},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def add_treatment(client: TestClient, token: str, category_id: int, name: str, price: int = 20000) -> int:
    r = client.post(
        "/treatments/",
        json={"name": name, "category_id": category_id, "default_price": price},
        headers={"Authorization": "Bearer {}".format(token)},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def make_shop(client: TestClient, key: str) -> Shop:
    email = "{}@example.com".format(key)
    password = "pw-{}".format(key)

    r = client.post("/auth/signup", json={"name": key, "email": email, "password": password})
    assert r.status_code == 200, r.text

    r = client.post("/auth/signin", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": "Bearer {}".format(token)}

    r = client.get("/users/me", headers=headers)
    assert r.status_code == 200, r.text
    user_id = r.json()["id"]

    customer_id = add_customer(client, token, user_id, "{}-고객".format(key))

    r = client.post("/categories/", json={"name": "{}-카테고리".format(key)}, headers=headers)
    assert r.status_code == 201, r.text
    category_id = r.json()["id"]

    treatment_id = add_treatment(client, token, category_id, "{}-커트".format(key))

    return Shop(token, user_id, category_id, customer_id, treatment_id)


@pytest.fixture
def shop_a(client: TestClient) -> Shop:
    return make_shop(client, "shop-a")


@pytest.fixture
def shop_b(client: TestClient) -> Shop:
    return make_shop(client, "shop-b")
