"""
시술 생성·수정 시 카테고리 소유권 검증 테스트 (티켓 20b).

- POST /treatments/ 에서 다른 가게·없는 category_id 를 쓰면 404, 시술 수 그대로
- PUT /treatments/{id} 에서 다른 가게·없는 category_id 로 옮기면 404, 시술 그대로
- 자기 카테고리로는 생성·수정·카테고리 이동이 정상
"""
from typing import Dict

from models.treatment import Treatment
from tests.conftest import Shop

MISSING_CATEGORY_ID = 999999


def treatment_body(category_id: int, name: str = "펌", price: int = 50000) -> Dict:
    return {"name": name, "category_id": category_id, "default_price": price}


def add_category(client, shop: Shop, name: str) -> int:
    r = client.post("/categories/", json={"name": name}, headers=shop.headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def treatment_count(db_session) -> int:
    db_session.expire_all()
    return db_session.query(Treatment).count()


def snapshot(db_session, treatment_id: int) -> Dict:
    db_session.expire_all()
    t = db_session.get(Treatment, treatment_id)
    assert t is not None
    return {
        "user_id": t.user_id,
        "name": t.name,
        "category_id": t.category_id,
        "default_price": t.default_price,
        "display_order": t.display_order,
    }


# ---------------- POST ----------------

def test_create_treatment_with_other_shops_category_returns_404(client, db_session, shop_a, shop_b):
    before = treatment_count(db_session)

    r = client.post("/treatments/", json=treatment_body(shop_b.category_id), headers=shop_a.headers)

    assert r.status_code == 404, r.text
    assert treatment_count(db_session) == before


def test_create_treatment_with_missing_category_returns_404(client, db_session, shop_a):
    before = treatment_count(db_session)

    r = client.post("/treatments/", json=treatment_body(MISSING_CATEGORY_ID), headers=shop_a.headers)

    assert r.status_code == 404, r.text
    assert treatment_count(db_session) == before


def test_other_shop_and_missing_category_give_same_response(client, shop_a, shop_b):
    """존재 여부가 새지 않도록 남의 카테고리와 없는 카테고리의 응답이 같아야 한다."""
    r_other = client.post("/treatments/", json=treatment_body(shop_b.category_id), headers=shop_a.headers)
    r_missing = client.post("/treatments/", json=treatment_body(MISSING_CATEGORY_ID), headers=shop_a.headers)

    assert r_other.status_code == r_missing.status_code == 404
    assert r_other.json() == r_missing.json()


def test_create_treatment_with_own_category_succeeds(client, db_session, shop_a):
    r = client.post("/treatments/", json=treatment_body(shop_a.category_id), headers=shop_a.headers)

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["category_id"] == shop_a.category_id
    assert body["display_order"] == 2  # make_shop 이 만든 커트 다음
    assert snapshot(db_session, body["id"])["user_id"] == shop_a.user_id


# ---------------- PUT ----------------

def test_update_treatment_to_other_shops_category_returns_404(client, db_session, shop_a, shop_b):
    before = snapshot(db_session, shop_a.treatment_id)

    r = client.put(
        "/treatments/{}".format(shop_a.treatment_id),
        json=treatment_body(shop_b.category_id, name="바뀐이름", price=1),
        headers=shop_a.headers,
    )

    assert r.status_code == 404, r.text
    assert snapshot(db_session, shop_a.treatment_id) == before


def test_update_treatment_to_missing_category_returns_404(client, db_session, shop_a):
    before = snapshot(db_session, shop_a.treatment_id)

    r = client.put(
        "/treatments/{}".format(shop_a.treatment_id),
        json=treatment_body(MISSING_CATEGORY_ID, name="바뀐이름", price=1),
        headers=shop_a.headers,
    )

    assert r.status_code == 404, r.text
    assert snapshot(db_session, shop_a.treatment_id) == before


def test_update_treatment_same_category_succeeds(client, db_session, shop_a):
    r = client.put(
        "/treatments/{}".format(shop_a.treatment_id),
        json=treatment_body(shop_a.category_id, name="커트-수정", price=25000),
        headers=shop_a.headers,
    )

    assert r.status_code == 200, r.text
    after = snapshot(db_session, shop_a.treatment_id)
    assert after["name"] == "커트-수정"
    assert after["default_price"] == 25000
    assert after["category_id"] == shop_a.category_id


def test_move_treatment_to_own_other_category_succeeds(client, db_session, shop_a):
    other_category_id = add_category(client, shop_a, "shop-a-두번째")

    r = client.put(
        "/treatments/{}".format(shop_a.treatment_id),
        json=treatment_body(other_category_id, name="커트", price=20000),
        headers=shop_a.headers,
    )

    assert r.status_code == 200, r.text
    assert r.json()["category_id"] == other_category_id
    assert snapshot(db_session, shop_a.treatment_id)["category_id"] == other_category_id
