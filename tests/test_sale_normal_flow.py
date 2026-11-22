"""
정상 흐름 회귀 테스트 (티켓 10).

본인 고객·본인 시술로 매출을 등록·수정할 때 상태코드·응답 형식·방문 회차가
수정 전과 동일하게 동작하는지 확인한다. (앱 업데이트 없이 배포돼야 하므로)
"""
from typing import Dict, List

from models.sale import Sale, SaleTreatment
from tests.conftest import add_customer, add_treatment
from tests.test_sale_tenant_isolation import SALE_DATE, create_own_sale, sale_body

SALE_KEYS = {
    "id",
    "user_id",
    "customer_id",
    "customer_name",
    "is_customer_deleted",
    "sale_date",
    "detail",
    "payment_type",
    "total_amount",
    "created_at",
    "treatments",
    "extra_prices",
    "num_of_visits",
}
SALE_TREATMENT_KEYS = {"id", "sale_id", "treatment_id", "treatment_name", "price"}


def post_sale(client, shop, customer_id: int, treatment_ids: List[int]) -> Dict:
    r = client.post("/sales/", json=sale_body(shop.user_id, customer_id, treatment_ids), headers=shop.headers)
    assert r.status_code == 200, r.text
    return r.json()


def put_sale(client, shop, sale_id: int, customer_id: int, treatment_ids: List[int], **overrides) -> Dict:
    body = sale_body(shop.user_id, customer_id, treatment_ids, sale_id=sale_id)
    body.update(overrides)
    r = client.put("/sales/", json=body, headers=shop.headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_create_own_sale_keeps_response_shape(client, shop_a):
    sale = create_own_sale(client, shop_a)

    assert set(sale.keys()) == SALE_KEYS
    assert sale["user_id"] == shop_a.user_id
    assert sale["customer_id"] == shop_a.customer_id
    assert sale["customer_name"] == "shop-a-고객"
    assert sale["is_customer_deleted"] is False
    assert sale["sale_date"] == SALE_DATE
    assert sale["payment_type"] == "card"
    assert sale["total_amount"] == 20000
    assert sale["extra_prices"] == {}
    assert sale["num_of_visits"] == 1

    assert len(sale["treatments"]) == 1
    st = sale["treatments"][0]
    assert set(st.keys()) == SALE_TREATMENT_KEYS
    assert st["sale_id"] == sale["id"]
    assert st["treatment_id"] == shop_a.treatment_id
    assert st["treatment_name"] == "shop-a-커트"
    assert st["price"] == 20000


def test_second_sale_for_same_customer_is_visit_2(client, shop_a):
    first = create_own_sale(client, shop_a)
    second = create_own_sale(client, shop_a)

    assert first["num_of_visits"] == 1
    assert second["num_of_visits"] == 2


def test_update_own_sale_with_other_own_customer_and_treatment(client, db_session, shop_a):
    sale = create_own_sale(client, shop_a)
    customer2 = add_customer(client, shop_a.token, shop_a.user_id, "shop-a-고객2")
    treatment2 = add_treatment(client, shop_a.token, shop_a.category_id, "shop-a-펌", price=80000)

    updated = put_sale(
        client, shop_a, sale["id"], customer2, [shop_a.treatment_id, treatment2],
        payment_type="cash", total_amount=100000, detail="수정됨",
    )

    assert set(updated.keys()) == SALE_KEYS
    assert updated["id"] == sale["id"]
    assert updated["customer_id"] == customer2
    assert updated["customer_name"] == "shop-a-고객2"
    assert updated["payment_type"] == "cash"
    assert updated["total_amount"] == 100000
    assert updated["detail"] == "수정됨"
    assert updated["num_of_visits"] == 1  # 고객2 의 첫 방문
    assert [t["treatment_name"] for t in updated["treatments"]] == ["shop-a-커트", "shop-a-펌"]
    for t in updated["treatments"]:
        assert set(t.keys()) == SALE_TREATMENT_KEYS

    db_session.expire_all()
    stored = db_session.get(Sale, sale["id"])
    assert stored.customer_id == customer2
    assert stored.payment_type == "cash"
    assert stored.total_amount == 100000
    stored_treatments = sorted(
        st.treatment_id
        for st in db_session.query(SaleTreatment).filter(SaleTreatment.sale_id == sale["id"]).all()
    )
    assert stored_treatments == sorted([shop_a.treatment_id, treatment2])


def test_visit_numbers_unchanged_in_normal_flow(client, shop_a, shop_b):
    customer2 = add_customer(client, shop_a.token, shop_a.user_id, "shop-a-고객2")

    s1 = create_own_sale(client, shop_a)                         # 고객1 1회차
    s2 = create_own_sale(client, shop_a)                         # 고객1 2회차
    b1 = create_own_sale(client, shop_b)                         # B 가게 매출은 A 회차에 영향 없음
    s3 = post_sale(client, shop_a, customer2, [shop_a.treatment_id])  # 고객2 1회차
    s4 = create_own_sale(client, shop_a)                         # 고객1 3회차

    assert [s1["num_of_visits"], s2["num_of_visits"], s4["num_of_visits"]] == [1, 2, 3]
    assert s3["num_of_visits"] == 1
    assert b1["num_of_visits"] == 1

    # 고객을 바꾸지 않는 수정 → 기존 회차 유지
    kept = put_sale(client, shop_a, s2["id"], shop_a.customer_id, [shop_a.treatment_id], total_amount=12345)
    assert kept["num_of_visits"] == 2

    # 고객을 바꾸는 수정 → 새 고객의 기존 매출 수 + 1 (고객2 는 이미 1건)
    moved = put_sale(client, shop_a, s1["id"], customer2, [shop_a.treatment_id])
    assert moved["num_of_visits"] == 2

    # 저장된 회차도 그대로
    r = client.get("/sales/by_customer/{}".format(shop_a.customer_id), headers=shop_a.headers)
    assert r.status_code == 200, r.text
    assert sorted(s["num_of_visits"] for s in r.json()) == [2, 3]
