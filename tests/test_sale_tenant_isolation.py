"""
KI-1 / KI-2 테넌트 격리 테스트 (티켓 10).

- KI-1: POST/PUT /sales/ 에서 다른 가게의 customer_id, treatment_id 를 쓰면 404
- KI-2: 방문 회차 count 가 다른 가게 매출과 섞이지 않는다
"""
from typing import Dict, List, Optional

from models.sale import Sale, SaleTreatment
from tests.conftest import Shop

SALE_DATE = "2026-01-15"  # 오늘 날짜 분기(datetime.now())를 피하기 위한 고정 과거 날짜


def sale_body(
    user_id: int,
    customer_id: int,
    treatment_ids: List[int],
    sale_id: Optional[int] = None,
) -> Dict:
    body = {
        "user_id": user_id,
        "customer_id": customer_id,
        "sale_date": SALE_DATE,
        "detail": None,
        "payment_type": "card",
        "total_amount": 20000 * len(treatment_ids),
        "treatments": [{"treatment_id": t, "price": 20000} for t in treatment_ids],
        "extra_prices": {},
    }
    if sale_id is not None:
        body["id"] = sale_id
    return body


def create_own_sale(client, shop: Shop) -> Dict:
    r = client.post(
        "/sales/",
        json=sale_body(shop.user_id, shop.customer_id, [shop.treatment_id]),
        headers=shop.headers,
    )
    assert r.status_code == 200, r.text
    return r.json()


def assert_sale_unchanged(db_session, shop: Shop, sale: Dict) -> None:
    """PUT 이 404 로 실패했을 때 기존 매출·기존 시술이 그대로인지 확인."""
    db_session.expire_all()
    stored = db_session.get(Sale, sale["id"])
    assert stored is not None
    assert stored.user_id == shop.user_id
    assert stored.customer_id == shop.customer_id
    assert stored.payment_type == sale["payment_type"]
    assert stored.total_amount == sale["total_amount"]
    assert stored.num_of_visits == sale["num_of_visits"]
    treatments = [
        (st.treatment_id, st.price)
        for st in db_session.query(SaleTreatment).filter(SaleTreatment.sale_id == sale["id"]).all()
    ]
    assert treatments == [(shop.treatment_id, 20000)]


def tampered_update_body(user_id: int, customer_id: int, treatment_ids: List[int], sale_id: int) -> Dict:
    """다른 필드도 바꿔서, 실패 시 일부만 반영되는지까지 잡아낸다."""
    body = sale_body(user_id, customer_id, treatment_ids, sale_id=sale_id)
    body["payment_type"] = "cash"
    body["total_amount"] = 99999
    return body


# ---------------- KI-1: POST ----------------

def test_create_sale_with_other_shops_customer_returns_404(client, db_session, shop_a, shop_b):
    r = client.post(
        "/sales/",
        json=sale_body(shop_a.user_id, shop_b.customer_id, [shop_a.treatment_id]),
        headers=shop_a.headers,
    )

    assert r.status_code == 404, r.text
    assert "shop-b-고객" not in r.text  # B 고객 이름이 새면 안 됨
    assert db_session.query(Sale).count() == 0


def test_create_sale_with_other_shops_treatment_returns_404(client, db_session, shop_a, shop_b):
    r = client.post(
        "/sales/",
        json=sale_body(shop_a.user_id, shop_a.customer_id, [shop_a.treatment_id, shop_b.treatment_id]),
        headers=shop_a.headers,
    )

    assert r.status_code == 404, r.text
    # 검증 실패 시 시술 없는 매출이 DB 에 남으면 안 됨
    assert db_session.query(Sale).count() == 0
    assert db_session.query(SaleTreatment).count() == 0


# ---------------- KI-1: PUT ----------------

def test_update_sale_with_other_shops_customer_returns_404(client, db_session, shop_a, shop_b):
    sale = create_own_sale(client, shop_a)

    r = client.put(
        "/sales/",
        json=tampered_update_body(shop_a.user_id, shop_b.customer_id, [shop_a.treatment_id], sale["id"]),
        headers=shop_a.headers,
    )

    assert r.status_code == 404, r.text
    assert "shop-b-고객" not in r.text
    assert_sale_unchanged(db_session, shop_a, sale)


def test_update_sale_with_other_shops_treatment_returns_404(client, db_session, shop_a, shop_b):
    sale = create_own_sale(client, shop_a)

    r = client.put(
        "/sales/",
        json=tampered_update_body(shop_a.user_id, shop_a.customer_id, [shop_b.treatment_id], sale["id"]),
        headers=shop_a.headers,
    )

    assert r.status_code == 404, r.text
    # 검증 실패 시 기존 매출이 일부 수정되거나 기존 시술이 지워진 채로 남으면 안 됨
    assert_sale_unchanged(db_session, shop_a, sale)


# ---------------- KI-2: 방문 회차 ----------------

def test_first_sale_of_shop_b_customer_is_visit_1(client, shop_a, shop_b):
    # A 가 B 의 고객으로 매출을 시도 (수정 후에는 404 로 막혀야 함 — 여기선 결과와 무관하게 진행)
    client.post(
        "/sales/",
        json=sale_body(shop_a.user_id, shop_b.customer_id, [shop_a.treatment_id]),
        headers=shop_a.headers,
    )

    sale = create_own_sale(client, shop_b)

    assert sale["num_of_visits"] == 1
