@../AGENTS.md

> 이 레포에서 Claude의 기본 역할은 **구현**이다 (AGENTS.md "역할별 규칙" 참고).

# Gopssl Backend — 프로젝트 컨텍스트

> AI 어시스턴트를 위한 백엔드 전체 컨텍스트 파일.
> 코드 작성 전 반드시 이 파일을 먼저 읽을 것.

## 프로젝트 개요

**Gopssl Backend**는 미용실 원장을 위한 매출/고객 관리 앱의 FastAPI 백엔드.
- 언어/프레임워크: Python 3.13 + FastAPI
- DB: PostgreSQL (SQLAlchemy ORM)
- 인증: JWT (jose) + bcrypt
- 배포: GitHub Actions — 브랜치에 머지(push)되면 자동 배포
  | 브랜치 | 환경 | 서버 | DB | 도메인 | systemd | 워크플로 |
  |--------|------|------|----|--------|---------|----------|
  | `main` | 운영 | AWS Lightsail | Supabase (서울) | api.gopssl.com | `gopssl-beta` (8001) | `deploy-production.yml` |
  | `dev` | 베타 | Oracle Cloud (OCI) | OCI 내부 Postgres | dev-api.gopssl.com | `gopssl.service` (8000) | `deploy-beta.yml` |
- 수동 배포: GitHub Actions 탭 → 해당 워크플로 → "Run workflow" (운영은 항상 main, 베타는 브랜치 선택 가능)
- systemd 서비스명(`gopssl-beta`)은 예전 이름 그대로다. Lightsail이 운영이다.

## 디렉터리 구조

```
Gopssl-Backend/
├── main.py                  # FastAPI 앱 엔트리포인트, 라우터 등록, CORS 설정
├── dependencies.py          # get_current_user (JWT → User 변환)
├── requirements.txt
│
├── database/
│   └── session.py           # DB 엔진, SessionLocal, get_db, Base
│
├── core/
│   ├── security.py          # 비밀번호 해싱, JWT 생성/검증
│   └── external/
│       └── kakao.py         # 카카오 주소 API 연동
│
├── models/                  # SQLAlchemy ORM 모델
│   ├── user.py
│   ├── customer.py
│   ├── sale.py              # Sale, SaleTreatment
│   └── treatment.py        # Treatment, TreatmentCategory
│
├── schemas/                 # Pydantic 스키마
│   ├── user.py
│   ├── customer.py
│   ├── sale.py
│   └── treatment.py
│
├── routers/                 # API 라우터
│   ├── auth.py              # /auth
│   ├── user.py              # /users
│   ├── customer.py          # /customers
│   ├── sale.py              # /sales
│   ├── saleStatistics.py    # /sales/statistics
│   ├── treatment.py         # /treatments
│   ├── treatmentCategory.py # /treatment-categories
│   └── address.py           # /address (카카오 주소 검색)
│
└── .github/workflows/
    ├── deploy-production.yml # 운영 자동 배포 (main → Lightsail)
    └── deploy-beta.yml       # 베타 자동 배포 (dev → OCI)
```

## 환경변수 (.env)

| 키 | 설명 |
|----|------|
| `DATABASE_URL` | PostgreSQL 연결 URL |
| `SECRET_KEY` | JWT 서명 키 |
| `ALGORITHM` | JWT 알고리즘 (HS256) |

## 참고 파일

- [API 명세](./api.md)
- [데이터 모델](./data-model.md)
- [배포 가이드](./deploy.md)
