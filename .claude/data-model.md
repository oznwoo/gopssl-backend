# 데이터 모델

## ERD 관계

```
User (1) ──< Customer (N)
User (1) ──< Sale (N)
User (1) ──< Treatment (N)
User (1) ──< TreatmentCategory (N)
Customer (1) ──< Sale (N)          ※ ondelete="SET NULL" — 고객 삭제 시 Sale.customer_id = NULL
Sale (1) ──< SaleTreatment (N)    ※ ondelete="CASCADE"
Treatment (1) ──< SaleTreatment (N) ※ ondelete="SET NULL"
TreatmentCategory (1) ──< Treatment (N)
```

---

## 모델 상세

### User
```python
id, name, email (unique), password (hashed),
store_name, address, address_detail, zip_code, created_at
```

### Customer
```python
id, user_id (FK→users, CASCADE),
name (default="신규"),   # ← "신규"는 의도된 기본값
phone_number, detail, created_at
```
> `sales` relationship: cascade **없음** (고객 삭제 시 매출 유지됨)

### Sale
```python
id, user_id (FK→users, CASCADE),
customer_id (FK→customers, SET NULL, nullable=True),  # 고객 삭제 후 NULL
sale_date (Date), detail, payment_type, total_amount,
num_of_visits, extra_prices (JSON), created_at
```

### SaleTreatment
```python
id, sale_id (FK→sales, CASCADE),
treatment_id (FK→treatments, SET NULL, nullable=True),
price
```

### Treatment
```python
id, user_id (FK→users, CASCADE),
name, default_price, category_id (FK→treatment_categories),
display_order
```

### TreatmentCategory
```python
id, user_id (FK→users, CASCADE),
name, display_order
```

---

## 주요 스키마

### CustomerCreate
```python
user_id: int
name: Optional[str] = "신규"
phone_number: Optional[str] = None
detail: Optional[str] = None
```

### SaleRead (중요)
```python
customer_id: Optional[int] = None   # nullable — 삭제된 고객 대응
customer_name: str                   # 항상 포함, 삭제 시 "알 수 없음"
```

### Token
```python
access_token: str
token_type: str
```

---

## 비즈니스 로직 메모

### 방문 회차 (num_of_visits)
- 매출 등록 시: 해당 customer_id의 기존 Sale 수 + 1로 계산해서 저장
- 매출 조회 시: 저장된 값 그대로 반환 (재계산 안 함)
- 고객 변경 시: 새 고객 기준으로 재계산

### 신규 고객 자동 정리
- 조건: `name = "신규"` AND `created_at < 현재 - 180일`
- 고객만 삭제, 연결된 Sale은 `customer_id = NULL`로 유지
- 엔드포인트: `DELETE /customers/cleanup/inactive`
- 호출 시점: 프론트엔드 앱 부팅 시 (자동 로그인 성공 후)

### 매출 통계
- 일별: 해당 월의 날짜별 총액 dict 반환
- 월별: 최근 4개월 비교 + 연도별(전년/올해) + 결제유형 건수 + 지난달 오늘까지 합계
