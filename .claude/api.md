# API 명세

## Base URL
```
https://<OCI_HOST>  (로컬: http://localhost:8000)
```

## 인증 방식
- JWT Bearer Token
- `Authorization: Bearer <token>` 헤더
- 토큰 만료: 24시간
- 만료 시 `/auth/refresh`로 갱신

---

## Auth `/auth`

| Method | Endpoint | 인증 | 설명 |
|--------|----------|------|------|
| POST | `/auth/signup` | ❌ | 회원가입 → 토큰 즉시 발급 |
| POST | `/auth/signin` | ❌ | 로그인 (form-urlencoded) |
| POST | `/auth/refresh` | ✅ | 토큰 갱신 |
| POST | `/auth/logout` | ✅ | 로그아웃 (클라이언트 토큰 삭제 안내) |

### 로그인 요청
```
Content-Type: application/x-www-form-urlencoded
Body: username=<email>&password=<password>
```

### 응답
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

---

## Users `/users`

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/users/me` | 내 정보 조회 |
| PUT | `/users/{id}` | 내 정보 수정 |

---

## Customers `/customers`

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/customers/` | 고객 등록 |
| GET | `/customers/` | 전체 고객 목록 |
| GET | `/customers/{id}` | 고객 단건 조회 |
| PUT | `/customers/{id}` | 고객 수정 |
| DELETE | `/customers/{id}` | 고객 삭제 |
| GET | `/customers/search?name=` | 고객 이름 검색 |
| DELETE | `/customers/cleanup/inactive` | 신규 고객 자동 정리 (6개월 이상) |

### 신규 고객 기본값
```json
{ "user_id": 1, "name": "신규", "phone_number": null, "detail": null }
```
> `name = "신규"`는 의도된 설계 — 빠른 매출 등록용. 건드리지 말 것.

---

## Sales `/sales`

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/sales/` | 매출 등록 |
| GET | `/sales/by_date?date=YYYY-MM-DD` | 날짜별 매출 |
| GET | `/sales/{id}` | 매출 단건 조회 |
| GET | `/sales/by_customer/{customer_id}` | 고객별 매출 전체 |
| PUT | `/sales/` | 매출 수정 |
| DELETE | `/sales/{id}` | 매출 삭제 |

### 주의
- `customer_id`는 `nullable=True` — 고객 삭제 시 NULL로 유지됨
- `customer_name`은 별도 필드로 응답에 항상 포함 (`"알 수 없음"` fallback)

---

## Sales Statistics `/sales/statistics`

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/sales/statistics/summary/daily?year=&month=` | 일별 매출 합계 (`{"YYYY-MM-DD": amount}`) |
| GET | `/sales/statistics/summary/monthly?year=&month=` | 월별 통계 (비교, 연도별, 결제유형) |

---

## Treatments `/treatments`

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/treatments/` | 시술 목록 (category_id, display_order 정렬) |
| GET | `/treatments/{id}` | 시술 단건 |
| POST | `/treatments/` | 시술 생성 |
| PUT | `/treatments/{id}` | 시술 수정 |
| DELETE | `/treatments/{id}` | 시술 삭제 (display_order 자동 재정렬) |
| POST | `/treatments/reorder` | 시술 순서 변경 `{treatment_id: new_order}` |

## Treatment Categories `/treatment-categories`

별도 라우터 (`treatmentCategory.py`)로 관리.

---

## 에러 응답 형식

```json
{ "detail": "에러 메시지" }          // 단일 에러
{ "detail": [{ "msg": "..." }] }    // 422 유효성 에러
```
