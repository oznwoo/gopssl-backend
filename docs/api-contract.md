# Gopssl API 계약 (v1 동작 고정)

Spring v2가 지켜야 할 현재 FastAPI 동작을 정리한 문서다. **기준은 코드(`routers/`, `schemas/`)다.** 기계가 읽는 스펙은 [`openapi.v1.json`](./openapi.v1.json)이고, `python scripts/export_openapi.py`로 다시 만든다.

OpenAPI에 드러나지 않는 것(상태 코드, 테넌트 규칙, 부수 효과)은 이 문서를 본다. 버그로 보이는 동작도 현재 동작이면 그대로 적고, [Known issues](#known-issues)에 따로 모았다.

**확인 방법:** 표의 상태 코드는 아래 환경에서 로컬 임시 DB에 실제로 호출해 확인했다. 예외로 "코드 기준"이라고 적은 항목은 호출하지 않고 코드만 읽었다. 카카오 API는 호출하지 않고 mock으로 대체했다.

| 환경 | Python | FastAPI | Pydantic | SQLAlchemy | 비고 |
|------|--------|---------|----------|------------|------|
| A | 3.8.20 | 0.124.4 | 2.10.6 | 2.0.55 | `requirements.txt` 새 설치 (psycopg2-binary는 wheel이 있는 2.9.9). **스냅샷 생성 환경** |
| B | 3.14.6 | 0.162.0 | 2.14.2 | 2.1.6 | 로컬 개발 venv |

두 환경의 상태 코드는 호출 123건 모두 같았다. 운영 서버의 패키지 버전은 확인하지 못했다.

---

## 공통 규칙

### 인증

- 방식: `Authorization: Bearer <JWT>` (HS256, `sub` = 사용자 id 문자열)
- 아래 표에서 인증 "✅"인 엔드포인트의 공통 실패 응답:

| 상황 | 상태 | `detail` |
|------|------|----------|
| 토큰 없음 | 401 | `Not authenticated` |
| 토큰 위조·형식 오류·만료 | 401 | `토큰이 유효하지 않거나 만료되었습니다.` |
| 토큰은 유효하지만 사용자가 삭제됨 | **404** | `사용자가 존재하지 않습니다.` |

### 토큰 수명

| 발급 경로 | `expires_delta` |
|-----------|-----------------|
| `POST /auth/signup` | 24시간 |
| `POST /auth/signin` | 24시간 |
| `POST /auth/refresh` | **30분** |

서버 시간대가 UTC가 아니면 실제 수명은 이 값과 다르다. [KI-8](#그-외-발견한-것) 참고.

### 오류 형식

```json
{ "detail": "메시지" }
```

요청 검증 실패는 422이고 `detail`이 배열이다.

```json
{ "detail": [{ "type": "missing", "loc": ["body", "name"], "msg": "Field required", "input": {} }] }
```

처리되지 않은 예외는 500이고 본문은 JSON이 아닌 `Internal Server Error` 텍스트다.

### 경로 끝 슬래시

경로는 표에 적힌 그대로 정확히 매칭된다. 슬래시가 다르면 **307 리다이렉트**한다. Spring은 기본 동작이 다르니 v2에서 확인이 필요하다.

- `GET /customers` → 307 → `/customers/`
- `POST /customers` → 307 → `/customers/`
- `GET /users/me/` → 307 → `/users/me`

### 날짜 형식

- `sale_date`: `YYYY-MM-DD`
- `created_at`, `deleted_at`: ISO 8601 (서버 UTC 환경에서 `2026-11-03T15:17:47.900557Z`). 단, `DELETE /customers/cleanup/inactive`만 `+00:00` 표기로 응답한다.

### 테넌트 규칙 표기

아래 표의 "테넌트" 열은 현재 사용자 소유를 확인하는 조건이다. **"없음"이나 "⚠️"는 소유 확인이 빠져 있다는 뜻이다.** v2로 옮길 때 그대로 따르지 말고 Known issues를 먼저 본다.

---

## Auth `/auth`

| Method | Path | 인증 | 요청 | 성공 | 실패 |
|--------|------|------|------|------|------|
| POST | `/auth/signup` | ❌ | JSON `UserCreate` | 200 `Token` | 400 이메일 중복, 422 |
| POST | `/auth/signin` | ❌ | **form** `username`(이메일), `password` | 200 `Token` | 401 이메일·비밀번호 불일치, 422 (JSON 본문을 보내도 422) |
| POST | `/auth/refresh` | ✅ | 없음 | 200 `Token` (30분) | 공통 |
| POST | `/auth/logout` | ✅ | 없음 | 200 `{"message"}` | 공통 |

- 테넌트: 해당 없음. refresh·logout은 토큰의 사용자 기준이다.
- `signin`의 Content-Type은 `application/x-www-form-urlencoded`다. `grant_type`, `scope`, `client_id`, `client_secret`도 받지만 코드에서 쓰지 않는다.
- `refresh`는 만료되지 않은 토큰이 있어야 호출할 수 있다. 별도의 refresh token은 없다.
- `logout`은 서버에서 토큰을 무효화하지 않는다. 호출 후에도 같은 토큰이 계속 유효하다.
- 회원가입은 201이 아니라 **200**이다.

```text
UserCreate  { name: str, email: EmailStr, password: str,
              store_name?: str, address?: str, address_detail?: str, zip_code?: str }
              ※ name·email·password만 저장된다 (KI-6)
Token       { access_token: str, token_type: "bearer" }
```

## Users `/users`

| Method | Path | 인증 | 요청 | 성공 | 실패 |
|--------|------|------|------|------|------|
| GET | `/users/me` | ✅ | 없음 | 200 `UserRead` | 공통 |
| PUT | `/users/me` | ✅ | JSON `UserUpdate` | 200 `UserRead` | 공통, 422, 500 이메일 중복 (KI-11) |
| DELETE | `/users/me` | ✅ | 없음 | 200 `{"message"}` | 공통 |

- 테넌트: 토큰의 사용자만 대상이다. `/users/{id}` 경로는 없다(404).
- `PUT`은 `null`이나 생략한 필드를 바꾸지 않는다. 그래서 값을 `null`로 지울 수 없다. `password`는 해싱해서 저장한다.
- `DELETE`: 시술은 ORM cascade로, 고객·매출은 DB `ON DELETE CASCADE`로 함께 삭제된다. 카테고리는 남는다 (KI-13).

```text
UserUpdate  { name?, email?: EmailStr, password?, store_name?, address?, address_detail?, zip_code? }
UserRead    { id: int, name: str|null, email: EmailStr, store_name: str|null, address: str|null,
              address_detail: str|null, zip_code: str|null, created_at: datetime }
```

## Customers `/customers`

| Method | Path | 인증 | 요청 | 성공 | 실패 | 테넌트 |
|--------|------|------|------|------|------|--------|
| POST | `/customers/` | ✅ | JSON `CustomerCreate` | 200 `CustomerRead` | 403 `user_id` 불일치, 422 | 바디 `user_id == 토큰 사용자` |
| GET | `/customers/` | ✅ | 없음 | 200 `CustomerRead[]` | 공통 | `Customer.user_id`, `is_deleted=false` (⚠️ 방문 수 조회는 KI-3) |
| GET | `/customers/deleted` | ✅ | 없음 | 200 `DeletedCustomerRead[]` (`deleted_at` 내림차순) | 공통 | `Customer.user_id`, `is_deleted=true` |
| GET | `/customers/{customer_id}` | ✅ | 없음 | 200 `CustomerRead` | 404, 422 | `Customer.user_id` |
| PUT | `/customers/{customer_id}` | ✅ | JSON `CustomerCreate` | 200 `CustomerRead` | 404, 403 `user_id` 불일치, 422 | `Customer.user_id`, `is_deleted=false`, 바디 `user_id` |
| DELETE | `/customers/{customer_id}` | ✅ | 없음 | 200 `{"message"}` | 404, 422 | `Customer.user_id` |
| POST | `/customers/{customer_id}/restore` | ✅ | 없음 | 200 `{"message"}` | 404, 400 삭제 상태 아님, 422 | `Customer.user_id` |
| DELETE | `/customers/{customer_id}/permanent` | ✅ | 없음 | 200 `{"message"}` | 404, 422 | `Customer.user_id` |
| DELETE | `/customers/cleanup/inactive` | ✅ | 없음 | 200 (아래) | 공통 | `Customer.user_id` |

**Soft delete 동작**

- `DELETE /customers/{id}`: `is_deleted=true`, `deleted_at=now`. 이미 삭제된 고객에게 다시 호출해도 200이고 `deleted_at`이 새 값으로 바뀐다.
- 삭제된 고객은 `GET /customers/`에서 빠지지만 **`GET /customers/{id}`로는 200으로 조회된다** (`is_deleted: true`).
- `PUT`은 삭제된 고객에게 404를 준다.
- `restore`: `is_deleted=false`, `deleted_at=null`.
- `permanent`: **soft delete 여부와 관계없이** 바로 행을 지운다. 연결된 매출은 남고 `customer_id`만 `NULL`이 된다.

**Cleanup:** `name == "신규"`이고 `created_at`이 180일보다 오래됐으며 삭제되지 않은 본인 고객을 soft delete한다. 대상이 없어도 200이다.

```json
{
  "deleted_count": 1,
  "deleted_customers": [
    { "id": 1, "name": "신규", "detail": null, "created_at": "...+00:00", "deleted_at": "...+00:00" }
  ]
}
```

**이름 기본값**

- `name` 생략 → `"신규"` (스키마 기본값)
- `name: null` → `"신규고객님"` (모델 기본값). 이 고객은 cleanup 대상이 아니다.

`PUT`은 보낸 필드만 바꾼다. 단 `user_id`는 필수다. `num_of_visits`는 고객의 최신 매출(`created_at` 기준)에 저장된 회차이고, 매출이 없으면 `null`이다. 목록 정렬은 지정되어 있지 않다.

```text
CustomerCreate       { user_id: int, name?: str = "신규", phone_number?: str, detail?: str }
CustomerRead         { id, user_id, name: str|null, phone_number: str|null, detail: str|null,
                       num_of_visits: int|null, created_at, is_deleted: bool, deleted_at: datetime|null }
DeletedCustomerRead  { id, name: str|null, detail: str|null, created_at, deleted_at: datetime|null }
```

## Sales `/sales`

| Method | Path | 인증 | 요청 | 성공 | 실패 | 테넌트 |
|--------|------|------|------|------|------|--------|
| POST | `/sales/` | ✅ | JSON `SaleCreate` | 200 `SaleRead` | 403 `user_id` 불일치, 404 시술 없음, 422, 500 고객 없음 | 바디 `user_id`만 ⚠️ `customer_id`, `treatment_id`는 소유 확인 없음 (KI-1) |
| GET | `/sales/` | ✅ | 없음 | 200 `[]` / **매출이 있으면 500** (KI-9) | 공통 | `Sale.user_id` |
| GET | `/sales/by_date?date=YYYY-MM-DD` | ✅ | 쿼리 | 200 `SaleRead[]` | 400 `date` 누락·형식 오류 | `Sale.user_id` |
| GET | `/sales/by_customer/{customer_id}` | ✅ | 없음 | 200 `SaleRead[]` (`sale_date` 오름차순) | 404 고객 없음, 422 | `Customer.user_id`, `Sale.user_id` |
| GET | `/sales/{sale_id}` | ✅ | 없음 | 200 `SaleRead` | 404, 422 | `Sale.user_id` |
| PUT | `/sales/` | ✅ | JSON `SaleUpdate` (`id`는 바디에) | 200 `SaleRead` | 404, 403 다른 사용자 매출·`user_id` 불일치, 422 | 기존 `Sale.user_id`, 바디 `user_id` ⚠️ KI-1 |
| DELETE | `/sales/{sale_id}` | ✅ | 없음 | 200 `{"message"}` | 404, 403 다른 사용자 매출, 422 | `Sale.user_id` |

- 다른 사용자의 매출은 `GET`이면 404, `PUT`·`DELETE`면 403이다 (KI-14).
- `by_date`에서 `date` 오류는 422가 아니라 **400**이다.
- `SaleCreate`의 `detail`, `payment_type`, `total_amount`는 `null`은 허용하지만 **키 자체는 필수**다. 빠지면 422.
- `customer_name`: 고객이 soft delete되었거나 없으면 `"삭제된"`이다. 이때 `is_customer_deleted: true`이고, 영구 삭제면 `customer_id: null`이다.
- `num_of_visits`
  - 생성: 해당 `customer_id`의 기존 매출 수 + 1 (⚠️ KI-2)
  - 수정: 고객이 바뀌면 새 고객 기준으로 다시 계산하고, 그대로면 유지한다.
  - 다른 매출의 회차는 삭제·수정 시 다시 계산하지 않는다 (코드 기준).
- `PUT`은 시술 목록을 전부 지우고 새로 넣는다.
- 시술이 삭제된 매출은 조회 시 500이 난다 (KI-10).

```text
SaleCreate   { user_id: int, customer_id: int, sale_date: date, detail: str|null, payment_type: str|null,
               total_amount: int|null, treatments: [{treatment_id: int, price: int}],
               extra_prices?: {str: int} = {} }
SaleUpdate   SaleCreate + { id: int }
SaleRead     { id, user_id, customer_id: int|null, customer_name: str, is_customer_deleted: bool,
               sale_date: date, detail: str|null, payment_type: str|null, total_amount: int|null,
               created_at, treatments: [SaleTreatmentRead], extra_prices: {str: int}|null,
               num_of_visits: int|null }
SaleTreatmentRead  { id, sale_id, treatment_id: int, price: int, treatment_name: str }
```

## Sales Statistics `/sales/statistics`

| Method | Path | 인증 | 요청 | 성공 | 실패 | 테넌트 |
|--------|------|------|------|------|------|--------|
| GET | `/sales/statistics/summary/daily` | ✅ | 쿼리 `year`(2000~2100), `month`(1~12) 필수 | 200 `{"YYYY-MM-DD": int}` | 422 | `Sale.user_id` |
| GET | `/sales/statistics/summary/monthly` | ✅ | 쿼리 `year`, `month` 필수 (범위 동일) | 200 (아래) | 422 | `Sale.user_id` |

`daily`는 매출이 있는 날짜만 키로 포함한다.

```json
{
  "monthly_comparison": [{ "year": 2026, "month": 8, "total": 0 }],
  "yearly_comparison": { "2025": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], "2026": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 300, 0] },
  "payment_type_count": { "card": 2 },
  "last_month_until_today_total": 0
}
```

- `monthly_comparison`: 요청한 달까지 4개월, 오래된 달부터. 이번 달은 오늘까지 합산한다.
- `yearly_comparison`: 키는 `year-1`, `year`이고 값은 12칸 배열이다. 올해의 지나지 않은 달은 0이다.
- `payment_type_count`: 키는 소문자이고 `null`은 제외한다 (⚠️ KI-15).
- `last_month_until_today_total`: 요청한 달의 전달 1일부터 `min(오늘 일자, 전달 말일)`까지의 합계.

## Treatments `/treatments`

| Method | Path | 인증 | 요청 | 성공 | 실패 | 테넌트 |
|--------|------|------|------|------|------|--------|
| GET | `/treatments/` | ✅ | 없음 | 200 `Treatment[]` (`category_id`, `display_order` 순) | 공통 | `Treatment.user_id` |
| GET | `/treatments/{treatment_id}` | ✅ | 없음 | 200 `Treatment` | 404, 422 | `Treatment.user_id` |
| POST | `/treatments/` | ✅ | JSON `TreatmentCreate` | **201** `Treatment` | 422, 500 카테고리 없음 | 토큰으로 `user_id` 지정 ⚠️ `category_id` 소유 확인 없음 (KI-12) |
| PUT | `/treatments/{treatment_id}` | ✅ | JSON `TreatmentCreate` | 200 `Treatment` | 404, 422 | `Treatment.user_id` ⚠️ KI-12 |
| DELETE | `/treatments/{treatment_id}` | ✅ | 없음 | **204** | 404, 422 | `Treatment.user_id` |
| POST | `/treatments/reorder` | ✅ | JSON `{ "<id>": <order> }` | 200 `{"message"}` | 404 하나라도 없거나 다른 사용자 소유, 422 | `Treatment.user_id` |

- 생성 시 `display_order` = 같은 카테고리의 본인 시술 수 + 1.
- 삭제 시 같은 카테고리에서 뒤에 있는 시술의 `display_order`가 1씩 줄어든다. 매출의 `treatment_id`는 `NULL`이 된다 (KI-10).
- `reorder`는 끝에서 한 번만 commit하므로 404가 나면 아무것도 바뀌지 않는다 (코드 기준).

```text
TreatmentCreate  { name: str, category_id: int, default_price: int }
Treatment        { id, name, category_id, default_price, display_order }   ※ user_id는 응답에 없음
```

## Categories `/categories`

`.claude/api.md`의 `/treatment-categories`는 **존재하지 않는다**(404). 실제 경로는 `/categories`다.

| Method | Path | 인증 | 요청 | 성공 | 실패 | 테넌트 |
|--------|------|------|------|------|------|--------|
| GET | `/categories/` | ✅ | 없음 | 200 `TreatmentCategory[]` (`display_order` 순) | 공통 | `TreatmentCategory.user_id` |
| GET | `/categories/{category_id}` | ✅ | 없음 | 200 `TreatmentCategory` | 404, 422 | `TreatmentCategory.user_id` |
| POST | `/categories/` | ✅ | JSON `{ name: str }` | **201** `TreatmentCategory` | 422 | 토큰으로 `user_id` 지정 |
| PUT | `/categories/{category_id}` | ✅ | JSON `{ name: str }` | 200 `TreatmentCategory` | 404, 422 | `TreatmentCategory.user_id` |
| DELETE | `/categories/{category_id}` | ✅ | 없음 | **204** | 404, 400 시술이 남아 있음, 422 | `TreatmentCategory.user_id` |
| POST | `/categories/reorder` | ✅ | JSON `{ "<id>": <order> }` | 200 `{"message"}` | 404, 422 | `TreatmentCategory.user_id` |

- 생성 시 `display_order` = 본인 카테고리 수 + 1. 삭제 시 뒤 순서가 1씩 줄어든다.
- 400 판정은 소유자와 관계없이 그 카테고리의 모든 시술을 본다 (KI-12).

```text
TreatmentCategory  { id, name, display_order }
```

## Address `/address`

| Method | Path | 인증 | 요청 | 성공 | 실패 | 테넌트 |
|--------|------|------|------|------|------|--------|
| GET | `/address/search?query=` | ✅ | 쿼리 `query` 필수 | 200 배열 (아래) | 공통, 422, 500 카카오 오류 (KI-11) | 해당 없음 (사용자 데이터 없음) |

```json
[{ "display_name": "...", "zone_no": "04524", "road_address": "...", "jibun_address": "...", "lat": "37", "lng": "127" }]
```

- `response_model`이 없어서 OpenAPI 스펙에는 응답 스키마가 없다. 이 형식이 계약이다.
- 도로명 주소가 있는 항목만 포함한다. `display_name`으로 중복을 제거하고 정렬한다.
- `lat`, `lng`는 숫자가 아니라 **문자열**이다 (카카오 `y`, `x` 값 그대로. 응답 형식은 코드 기준이고 실제 카카오 응답으로는 확인하지 못했다).
- 키워드 검색 결과마다 카카오 주소 API를 한 번씩 더 호출한다.

---

## Known issues

**수정하지 않고 기록만 한다.** "확인"은 임시 DB에 실제로 호출해 재현했다는 뜻이고, "코드"는 코드만 읽어 판단했다는 뜻이다.

### 티켓에서 확인을 요청한 항목

| ID | 내용 | 결과 | 근거 |
|----|------|------|------|
| KI-1 | `POST`·`PUT /sales/`가 `customer_id`, `treatments[].treatment_id`의 소유자를 검증하지 않아 **다른 가게 고객·시술 이름이 노출된다** (테넌트 격리 위반) | **사실. 확인** | `routers/sale.py:62,86,337,360`. A가 B의 고객·시술로 매출을 만들면 200과 함께 `customer_name`, `treatment_name`에 B의 값이 온다. `PUT`도 같다. 이후 `GET /sales/{id}`로도 계속 보인다. |
| KI-2 | 방문 회차 count 쿼리에 `user_id` 조건이 없다 | **사실. 확인** | `routers/sale.py:38-42,308-312`. KI-1과 합쳐지면 A의 매출이 B 고객의 회차를 올린다. B의 첫 매출이 `num_of_visits: 2`로 저장되는 것을 재현했다. |
| KI-3 | `GET /customers/` 최신 매출 서브쿼리가 전체 사용자 매출을 스캔한다 (성능) | **사실. 코드** | `routers/customer.py:37-54`. 두 쿼리 모두 `user_id` 조건이 없다. 결과는 본인 고객에만 매핑되므로 이 쿼리만으로는 노출이 없다. 성능 측정은 하지 않았다. |
| KI-4 | 요청 바디의 `user_id`를 받아 비교한다 (v2에서는 토큰 사용자로만 결정 권장) | **사실. 확인** | `routers/customer.py:18,199`, `routers/sale.py:21,287`. 불일치 시 403, 누락 시 422다. 시술·카테고리는 이미 토큰으로 결정한다. |
| KI-5 | `/auth/refresh`가 30분 토큰을 발급한다 (로그인은 24시간) | **사실. 확인** | `routers/auth.py:59`. 서버 시간대 UTC에서 남은 시간 30.0분, 로그인은 1440.0분. 시간대 문제는 KI-8. |
| KI-6 | `/auth/signup`이 `store_name`을 받지만 저장하지 않는다 | **사실. 확인** | `routers/auth.py:23-27`. `address`, `address_detail`, `zip_code`도 마찬가지다. 가입 직후 `/users/me`에서 모두 `null`이고, `PUT /users/me`로는 저장된다. |
| KI-7 | `requirements.txt`에 SQLAlchemy 등의 버전이 고정되어 있지 않다 | **미고정은 사실. "서버가 안 뜸"은 조건부** | 아래 참고. |

**KI-7 상세:** `bcrypt`만 고정되어 있다. 실제 결과는 Python 버전과 URL 형식에 따라 갈렸다.

| Python | 설치된 SQLAlchemy | `DATABASE_URL` | 결과 |
|--------|------------------|----------------|------|
| 3.8 | 2.0.55 | `postgresql+psycopg2://` | 서버 기동, 호출 정상 |
| 3.14 | 2.1.6 | `postgresql+psycopg2://` | 서버 기동, 호출 정상 |
| 3.14 | 2.1.6 | `postgresql://` | **기동 실패** `ModuleNotFoundError: No module named 'psycopg'` (드라이버 미지정 시 psycopg3를 찾는다) |

Python 3.8에서 드라이버 미지정 URL, 그리고 운영 서버의 실제 조합은 확인하지 못했다. 또한 macOS arm64 + Python 3.8에서는 `psycopg2-binary` 최신 해석 버전의 wheel이 없어 소스 빌드가 실패했고, `--only-binary`를 줘야 설치됐다 (리눅스 운영 서버에서 같은지는 확인하지 못했다).

### 그 외 발견한 것

| ID | 내용 | 결과 | 근거 |
|----|------|------|------|
| KI-8 | **토큰 만료 시각이 서버 시간대에 따라 어긋난다.** `datetime.utcnow().timestamp()`가 UTC 값을 로컬 시각으로 해석한다. | **확인** | `core/security.py:20-22`. `TZ=Asia/Seoul`에서 로그인 토큰의 남은 시간은 900분(15시간), `/auth/refresh` 토큰은 **-510분으로 발급 즉시 만료**되어 다음 호출이 401이다. `TZ=UTC`에서는 정상이다. 운영 서버의 시간대는 확인하지 못했다. |
| KI-9 | **`GET /sales/`는 매출이 하나라도 있으면 500이다.** ORM 객체에 `customer_name`이 없어 응답 검증에 실패한다. | **확인** | `routers/sale.py:113-114`, `schemas/sale.py`. 매출이 없으면 200 `[]`. |
| KI-10 | **시술을 삭제하면 그 시술이 포함된 매출 조회가 500이다.** `treatment_id`가 `NULL`이 되는데 `treatment_name: str`이 필수이고, `by_date`는 `st.treatment.category`도 읽는다. | **확인** | `GET /sales/{id}`, `/sales/by_date`, `/sales/by_customer/{id}` 모두 재현. `routers/sale.py`, `schemas/sale.py:17`. |
| KI-11 | 입력 오류가 처리되지 않고 500이 된다. | **확인** | `POST /sales/` 없는 `customer_id`, `POST /treatments/` 없는 `category_id`, `PUT /users/me` 중복 이메일, 컬럼 길이 초과(`phone_number` 30자), 카카오 HTTP 오류, 카카오 응답의 `address: null` (`routers/address.py:34`, mock으로 재현). |
| KI-12 | **시술의 `category_id` 소유자를 검증하지 않는다** (테넌트 격리 위반). B의 시술을 A의 카테고리에 넣을 수 있고, 그러면 A는 그 카테고리를 지울 수 없다(400). | `POST` 확인, `PUT`은 코드 | `routers/treatment.py:58,85-86`, `routers/treatmentCategory.py:100`. |
| KI-13 | `DELETE /users/me` 후 카테고리가 `user_id = NULL`로 DB에 남는다. | **확인** | `models/treatment.py:29`. ORM relationship에 cascade가 없어 FK의 `ON DELETE CASCADE` 전에 `NULL`로 바뀐다. |
| KI-14 | 다른 사용자 매출에 대한 응답이 일관되지 않다. `GET`은 404, `PUT`·`DELETE`는 403이라 매출 id의 존재 여부를 알 수 있다. | **확인** | `routers/sale.py:262-266,391-396`. |
| KI-15 | `payment_type_count`가 대소문자만 다른 값을 합치지 않고 덮어쓴다. | **확인** | `routers/saleStatistics.py:68`. `Card` 2건 + `card` 1건이 `{"card": 2}`로 나왔다. 어느 값이 남는지는 쿼리 순서에 달려 있다. |
| KI-16 | **매출 저장이 원자적이지 않다.** 없는 `treatment_id`로 `POST`하면 404인데 매출은 남고, `PUT`하면 404인데 기존 시술이 지워진다. | **확인** | `routers/sale.py:57,62-67,332-341`. `POST` 후 매출 수 3→4, `PUT` 후 시술 수 1→0. |
| KI-17 | 고객 삭제 동작의 경계가 느슨하다. soft delete된 고객을 단건 조회할 수 있고, 다시 삭제하면 `deleted_at`이 바뀌며, soft delete 없이 바로 영구 삭제된다. | **확인** | `routers/customer.py`. 의도된 동작인지 확인이 필요하다. |
| KI-18 | 신규 고객 기본 이름이 두 개다. 스키마 `"신규"`, 모델 `"신규고객님"`. `name: null`로 만든 고객은 cleanup에서 빠진다. | **확인** | `schemas/customer.py:7`, `models/customer.py:11`. |
| KI-19 | `logout`이 토큰을 무효화하지 않고, 삭제된 사용자의 토큰은 401이 아니라 404를 받는다. | **확인** | `routers/auth.py`, `dependencies.py`. |
| KI-20 | 매출 삭제나 고객 변경 후 회차를 다시 계산하지 않아, 같은 고객에게 같은 회차가 생길 수 있다. | 코드 | `routers/sale.py:292-315`. |

---

## `.claude/api.md`와 코드의 차이

코드가 기준이다. `api.md`는 이 티켓에서 고치지 않았다.

| `api.md` | 실제 코드 |
|----------|-----------|
| `/treatment-categories` | `/categories` |
| `PUT /users/{id}` | `PUT /users/me` (`/users/{id}`는 404) |
| `GET /customers/search?name=` | 없음 (`customer_id` 파싱 실패로 422) |
| 삭제 고객의 `customer_name`은 `"알 수 없음"` | `"삭제된"` |
| 토큰 만료 24시간 | refresh로 받은 토큰은 30분 |
| 표에 없음 | `DELETE /users/me`, `GET /sales/`, `/customers/deleted`, `/restore`, `/permanent` |
| 고객 기본값 `"신규"` | 스키마 `"신규"`, 모델 `"신규고객님"` (KI-18). `data-model.md`도 같다. |
