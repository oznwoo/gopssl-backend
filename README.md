<h1 align="center">
  <br/>
  Gopssl Backend
  <br/>
</h1>

<p align="center">
  <a href="https://github.com/oh0227/Gopssl-frontend">Gopssl-frontend</a>와 세트로 동작하는 매출 · 고객 관리 앱의 FastAPI 백엔드
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLAlchemy-ORM-d71f00?style=flat-square" />
  <img src="https://img.shields.io/badge/Auth-JWT-000000?style=flat-square&logo=jsonwebtokens" />
  <img src="https://img.shields.io/badge/Status-Operating-yellow?style=flat-square" />
</p>

---

## 소개

Gopssl Backend는 워크인 위주로 운영되는 소규모 미용실 원장을 위한 매출 · 고객 관리 앱 [Gopssl-frontend](https://github.com/oh0227/Gopssl-frontend)의 API 서버다. 회원 인증, 고객/매출/시술 데이터 관리, 매출 통계 집계, 카카오 주소 검색 연동을 담당한다.

2025-07-20 첫 커밋 이후 약 11개월째 47개 커밋으로 운영 중이며, Oracle Cloud(OCI) 인스턴스에서 상시 구동된다.

---

## 기술 스택

| 영역 | 기술 | 비고 |
|---|---|---|
| 언어 | Python 3.13 | |
| 프레임워크 | FastAPI | |
| ORM | SQLAlchemy | 커넥션 풀(`pool_size=5`, `max_overflow=10`) 설정 |
| 데이터베이스 | PostgreSQL | `psycopg2-binary` 드라이버 |
| 인증 | JWT (`python-jose`) + `bcrypt` | OAuth2PasswordBearer 기반 |
| 외부 API | httpx | 카카오 로컬 API(주소 검색) 비동기 호출 |
| 배포 | Oracle Cloud (OCI) + systemd | `gopssl.service` |
| CI/CD | GitHub Actions | `dev` 브랜치 push 시 SSH 자동 배포 |

---

## 도메인 모델

```
User(원장)
 ├─ 1:N ─ Treatment(시술) ─ N:1 ─ TreatmentCategory(카테고리)
 ├─ 1:N ─ Customer(고객)
 └─ 1:N ─ Sale(매출) ─ N:1 ─ Customer

Sale ─ 1:N ─ SaleTreatment ─ N:1 ─ Treatment   (매출-시술 다대다 조인 테이블)
```

- **Customer 소프트 삭제** (`is_deleted` / `deleted_at`): 고객을 즉시 삭제하면 연결된 `Sale.customer_id` 참조가 끊겨 과거 매출 통계가 왜곡된다. 목록에서 숨기는 것과 실제 삭제를 분리했다.
- **Sale.extra_prices (JSON 컬럼)**: 팁, 재료비 등 매장마다 다른 부가 항목을 고정 컬럼으로 미리 정의하지 않고 유연하게 저장하기 위해 JSON으로 뒀다.
- **Sale.num_of_visits (방문 회차 스냅샷)**: 방문 횟수를 매번 실시간으로 재계산하지 않고 매출 생성 시점의 값을 그대로 저장해, 이후 다른 매출이 추가/삭제되어도 과거 매출 기록의 방문 회차가 바뀌지 않도록 했다.

---

## API 라우터

| 라우터 | prefix | 핵심 기능 |
|---|---|---|
| `user` | `/users` | 본인 정보 조회/수정/삭제 (본인 리소스만 접근 가능) |
| `customer` | `/customers` | CRUD, 소프트 삭제/복구/영구삭제, 미방문 고객 자동 정리 |
| `sale` | `/sales` | 매출 CRUD, 날짜별·고객별 조회 |
| `saleStatistics` | `/sales/statistics` | 일별/월별 매출 집계, 기간 비교 |
| `auth` | `/auth` | 회원가입 · 로그인 · 토큰 갱신 · 로그아웃 |
| `address` | `/address` | 카카오 API 기반 통합 주소 검색 |
| `treatment` | `/treatments` | 시술 CRUD, 순서 변경(reorder) |
| `treatmentCategory` | `/categories` | 시술 카테고리 CRUD, 순서 변경(reorder) |

---

## 엔지니어링 하이라이트

### JWT 기반 인증 + 전 라우터 소유권 검증

**문제**: 인증만 걸고 소유권 검증을 빠뜨리면, 로그인한 사용자가 토큰만 유효하면 자신이 아닌 다른 원장의 고객/매출 데이터에도 접근할 수 있게 된다(수평 권한 상승).

**해결**: `OAuth2PasswordBearer` + JWT로 인증을 처리하고, `customer`/`sale`/`treatment`/`treatmentCategory`의 모든 조회·수정·삭제 엔드포인트에서 요청 리소스의 `user_id`와 `current_user.id`를 대조해 일치하지 않으면 403/404로 차단한다.

파일: [dependencies.py](dependencies.py), [core/security.py](core/security.py), `routers/` 전체

### N+1 쿼리 최적화

**문제**: `GET /customers/`에서 고객 목록을 조회한 뒤 고객별 최신 방문 회차를 구하기 위해 고객 수만큼 반복 쿼리가 발생했다. 고객이 100명이면 목록 조회 1번 + 방문 회차 조회 100번, 총 101번의 쿼리가 나가는 구조였다.

**해결**: 고객별 `Sale.created_at` 최댓값을 구하는 서브쿼리를 만들고, 이를 `Sale`과 JOIN해 모든 고객의 최신 방문 회차를 한 번의 쿼리로 가져오도록 리팩토링했다.

- Before: 고객 수만큼 개별 쿼리 반복 (N+1)
- After: 서브쿼리 + JOIN 1회로 축소

커밋: `c232b45` · 파일: [routers/customer.py](routers/customer.py)

### 환경변수 일원화 + fail-fast 검증

**문제**: 환경변수 로딩 로직이 여러 파일에 흩어져 있으면 배포 시 값이 빠져도 앱이 일단 기동되고, 실제 요청이 들어와서야 에러가 터지는 상황이 생길 수 있다.

**해결**: `core/config.py` 하나로 모든 `os.getenv` 호출을 모으고, `DATABASE_URL`/`SECRET_KEY`처럼 필수 값이 비어 있으면 모듈 import 시점에 `RuntimeError`를 던져 앱이 아예 부팅되지 않게 했다.

파일: [core/config.py](core/config.py) · 커밋: `9485823`, `00e267d`

### 카카오 주소 통합 검색

**문제**: 카카오 keyword API는 검색 범위는 넓지만 정확한 우편번호·도로명이 없고, address API는 정확하지만 검색어가 정확한 주소 형태여야 결과가 나온다.

**해결**: keyword API로 후보를 넓게 검색한 뒤, 각 결과의 주소명을 다시 address API로 조회해 우편번호·도로명·지번주소를 붙였다. 응답에서 `display_name` 기준 중복을 제거하고 가나다순 정렬까지 서버에서 처리해, 프론트가 추가 가공 없이 바로 쓸 수 있는 형태로 내려준다.

파일: [core/external/kakao.py](core/external/kakao.py), [routers/address.py](routers/address.py)

### 소프트 삭제 도메인 모델링

**문제**: 고객을 즉시 삭제(hard delete)하면 해당 고객이 연결된 매출 기록의 참조가 끊기고, 월별/연도별 매출 통계가 왜곡된다.

**해결**: `Customer.is_deleted` / `deleted_at` 플래그로 목록에서만 제외하고, `Sale.customer_id`는 `ondelete="SET NULL"`로 설정해 고객을 영구 삭제해도 매출 레코드 자체(금액, 날짜, 시술 내역)는 보존되게 했다. 복구(`/restore`)와 영구 삭제(`/permanent`)를 별도 엔드포인트로 분리해 되돌릴 수 있는 삭제와 되돌릴 수 없는 삭제를 구분했다.

파일: [models/customer.py](models/customer.py), [models/sale.py](models/sale.py), [routers/customer.py](routers/customer.py)

### 통계 API

**문제**: 원장이 "이번 달이 지난달보다 나은지"를 감으로만 판단해야 했다.

**해결**: `extract("year"/"month", ...)`로 기간을 필터링하고 `func.sum`/`func.count`로 집계한 뒤, `defaultdict`로 연도별 12개월 매출 배열을 채워 최근 4개월 비교·전년 대비 비교·결제수단별 건수를 한 번의 요청으로 반환한다.

파일: [routers/saleStatistics.py](routers/saleStatistics.py)

### CI/CD

**문제**: 매 배포마다 SSH 접속, `git pull`, 서비스 재시작을 수동으로 반복해야 했다.

**해결**: `dev` 브랜치에 push가 발생하면 GitHub Actions가 `appleboy/ssh-action`으로 OCI 인스턴스에 접속해 `git pull origin dev` 후 `systemctl restart gopssl.service`까지 자동 실행한다.

파일: [.github/workflows/deploy.yml](.github/workflows/deploy.yml)

---

## 폴더 구조

```
Gopssl-Backend/
├── main.py                    # FastAPI 앱 엔트리포인트, 라우터 등록, CORS 설정
├── dependencies.py            # get_current_user (JWT → User 변환)
├── requirements.txt
├── core/
│   ├── config.py               # 환경변수 일원화 + 필수값 fail-fast 검증
│   ├── security.py             # bcrypt 해싱, JWT 발급/검증
│   └── external/
│       └── kakao.py            # 카카오 주소 API 연동
├── database/
│   └── session.py              # DB 엔진, 커넥션 풀, get_db 세션 의존성
├── models/                     # SQLAlchemy ORM 모델
│   ├── user.py
│   ├── customer.py
│   ├── sale.py                 # Sale, SaleTreatment
│   └── treatment.py            # Treatment, TreatmentCategory
├── schemas/                    # Pydantic 요청/응답 스키마
│   ├── user.py
│   ├── customer.py
│   ├── sale.py
│   └── treatment.py
├── routers/                     # API 라우터
│   ├── auth.py
│   ├── user.py
│   ├── customer.py
│   ├── sale.py
│   ├── saleStatistics.py
│   ├── treatment.py
│   ├── treatmentCategory.py
│   └── address.py
└── .github/workflows/
    └── deploy.yml               # OCI 자동 배포 (dev 브랜치 push 트리거)
```

---

## 배포 및 CI/CD

Oracle Cloud(OCI) 인스턴스에서 FastAPI 앱을 `gopssl.service`라는 systemd 서비스로 상시 구동한다.

`dev` 브랜치에 push되면 GitHub Actions 워크플로([deploy.yml](.github/workflows/deploy.yml))가 트리거되어:

1. `appleboy/ssh-action`으로 OCI 서버에 SSH 접속
2. `git checkout dev && git pull origin dev`로 최신 코드 반영
3. `systemctl restart gopssl.service`로 서비스 재시작 및 상태 확인

별도의 빌드 단계 없이 코드를 pull하고 서비스를 재시작하는 경량 배포 방식이다.

---

## 시작하기

```bash
git clone https://github.com/oh0227/Gopssl-Backend.git
cd Gopssl-Backend

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # DATABASE_URL, SECRET_KEY, KAKAO_REST_API_KEY 등 설정

uvicorn main:app --reload
```

앱 기동 시 `Base.metadata.create_all(bind=engine)`이 실행되어 정의된 테이블이 없으면 자동 생성된다. 별도의 마이그레이션 도구는 아직 사용하지 않는다.

---

## 현재 상태 및 로드맵

혼자 개발 · 운영하고 있는 프로젝트라, 알려진 한계를 그대로 남겨둔다.

- **자동화된 테스트가 없다.** 현재 pytest 기반 테스트가 전혀 없어 회귀를 수동으로 확인하고 있다. `auth`, `sale` 라우터부터 통합 테스트를 추가할 계획이다.
- **DB 스키마 마이그레이션 도구가 없다.** `Base.metadata.create_all()`로 없는 테이블만 생성하는 방식이라, 기존 테이블의 컬럼 변경은 수동으로 처리해야 한다. Alembic 도입을 검토 중이다.
- **목록 조회 API에 페이지네이션이 없다.** `GET /customers/`, `GET /sales/` 모두 조건에 맞는 전체 행을 한 번에 반환한다. 데이터가 늘어나면 응답 크기와 조회 시간에 영향을 줄 수 있다.
- **엔드포인트에 별도의 rate limiting이 없다.** 로그인 등 민감한 엔드포인트도 요청 횟수 제한이 걸려 있지 않다.
- **`/auth/refresh`의 토큰 만료 시간이 로그인/회원가입과 다르다.** 로그인·회원가입은 24시간짜리 토큰을 발급하는데 refresh는 30분짜리를 발급해, 갱신할수록 세션이 오히려 짧아지는 불일치가 있다. 정리가 필요하다.
- `core/security.py`의 JWT 예외 처리에 `print()`로 남긴 디버깅 로그가 있다. 운영 로깅 체계로 교체할 예정이다.

---

## 커밋 히스토리

총 47개 커밋. 2025-07-20 첫 커밋 이후 약 11개월째 이어지고 있다.
