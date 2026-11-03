"""
Gopssl 개발 DB 더미 데이터 시드 스크립트

- 실제 API(/auth/signup, /categories, /treatments, /customers, /sales)를 호출해서
  앱과 똑같은 비즈니스 로직(방문 회차 계산 등)으로 데이터를 만든다.
- 테넌트 격리 테스트용으로 가게 2곳(A, B)을 만든다.
- 기본은 localhost에만 실행된다. 다른 서버는 SEED_ALLOWED_HOSTS로 명시해야 한다.

사용법 (gopssl-backend 레포 루트에서, 개발 DB를 바라보는 로컬 서버를 띄운 상태로):
    python scripts/seed_dev.py                      # 기본: http://localhost:8000
    BASE_URL=http://localhost:8000 python scripts/seed_dev.py
"""

import os
import random
import sys
from datetime import date, timedelta

from urllib.parse import urlparse

import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

# 허용 목록 방식: 기본은 로컬만 허용한다. (운영 서버 주소를 코드에 적지 않기 위해)
# 개발 서버에 시드해야 할 때만 SEED_ALLOWED_HOSTS=<호스트>로 명시적으로 연다.
ALLOWED_HOSTS = {"localhost", "127.0.0.1"} | {
    h.strip() for h in os.getenv("SEED_ALLOWED_HOSTS", "").split(",") if h.strip()
}

_host = urlparse(BASE_URL).hostname
if _host not in ALLOWED_HOSTS:
    sys.exit(f"[중단] 허용되지 않은 대상({BASE_URL})입니다. 로컬이 아니면 SEED_ALLOWED_HOSTS로 명시하세요.")

random.seed(42)

SHOPS = [
    {"name": "테스트원장A", "email": "shop-a@gopssl.dev", "password": "test1234!", "store_name": "테스트미용실 A"},
    {"name": "테스트원장B", "email": "shop-b@gopssl.dev", "password": "test1234!", "store_name": "테스트미용실 B"},
]

CATALOG = {
    "커트": [("여성 커트", 20000), ("남성 커트", 15000), ("앞머리 커트", 5000)],
    "펌": [("일반 펌", 60000), ("셋팅 펌", 90000), ("매직", 100000), ("다운펌", 20000)],
    "염색": [("전체 염색", 70000), ("뿌리 염색", 40000), ("새치 염색", 35000)],
    "클리닉": [("두피 클리닉", 30000), ("모발 클리닉", 40000)],
}

LAST_NAMES = list("김이박최정강조윤장임한오서신권황안송류홍")
FIRST_NAMES = ["민지", "서연", "지현", "수빈", "영희", "미경", "은주", "정숙", "순자", "현우",
               "지훈", "도윤", "하은", "예린", "경희", "말순", "옥자", "선영", "혜진", "유진"]


def signup_or_login(client: httpx.Client, shop: dict) -> str:
    r = client.post("/auth/signup", json={
        "name": shop["name"], "email": shop["email"], "password": shop["password"],
        "store_name": shop["store_name"],
    })
    if r.status_code == 400:  # 이미 가입됨 → 로그인
        r = client.post("/auth/signin", data={"username": shop["email"], "password": shop["password"]})
    r.raise_for_status()
    return r.json()["access_token"]


def seed_shop(shop: dict, n_customers: int, n_sales: int) -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        token = signup_or_login(client, shop)
        client.headers["Authorization"] = f"Bearer {token}"
        me = client.get("/users/me").json()
        user_id = me["id"]

        existing = client.get("/customers/").json()
        if existing:
            print(f"- {shop['store_name']}: 이미 고객 {len(existing)}명 있음 → 건너뜀")
            return

        # 시술 카테고리 + 시술
        treatments = []
        for cat_name, items in CATALOG.items():
            cat = client.post("/categories/", json={"name": cat_name})
            cat.raise_for_status()
            cat_id = cat.json()["id"]
            for t_name, price in items:
                t = client.post("/treatments/", json={"name": t_name, "category_id": cat_id, "default_price": price})
                t.raise_for_status()
                treatments.append(t.json())

        # 고객 (일부는 이름 없는 '신규' 고객)
        customer_ids = []
        for i in range(n_customers):
            is_new = random.random() < 0.15
            body = {
                "user_id": user_id,
                "name": "신규" if is_new else random.choice(LAST_NAMES) + random.choice(FIRST_NAMES),
                "phone_number": None if is_new else f"010-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                "detail": random.choice([None, "두피 민감", "곱슬 심함", "단골", "염색약 알레르기 주의", None]),
            }
            c = client.post("/customers/", json=body)
            c.raise_for_status()
            customer_ids.append(c.json()["id"])

        # 매출: 최근 120일, 오래된 날짜부터 순서대로 (방문 회차가 자연스럽게 쌓이도록)
        today = date.today()
        dates = sorted(today - timedelta(days=random.randint(0, 120)) for _ in range(n_sales))
        regulars = customer_ids[: max(5, n_customers // 4)]  # 자주 오는 단골
        for d in dates:
            cid = random.choice(regulars) if random.random() < 0.5 else random.choice(customer_ids)
            picked = random.sample(treatments, k=random.choice([1, 1, 1, 2]))
            items = [{"treatment_id": t["id"], "price": t["default_price"]} for t in picked]
            extra = {"기장 추가": 10000} if random.random() < 0.1 else {}
            total = sum(i["price"] for i in items) + sum(extra.values())
            s = client.post("/sales/", json={
                "user_id": user_id,
                "customer_id": cid,
                "sale_date": d.isoformat(),
                "detail": None,
                "payment_type": random.choice(["현금", "카드", "카드", "카드"]),
                "total_amount": total,
                "treatments": items,
                "extra_prices": extra,
            })
            s.raise_for_status()

        print(f"- {shop['store_name']} ({shop['email']}): 시술 {len(treatments)}개, 고객 {n_customers}명, 매출 {n_sales}건 생성")


if __name__ == "__main__":
    print(f"시드 대상: {BASE_URL}")
    seed_shop(SHOPS[0], n_customers=40, n_sales=150)
    seed_shop(SHOPS[1], n_customers=10, n_sales=30)
    print("완료. 테스트 계정 비밀번호: test1234!")
