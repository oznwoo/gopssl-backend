# 배포 가이드

## 인프라

| 환경 | 브랜치 | 서버 | DB | 도메인 | systemd (포트) | 앱 디렉터리 | 워크플로 |
|------|--------|------|----|--------|----------------|-------------|----------|
| 운영 | `main` | AWS Lightsail (Ubuntu) | Supabase (서울) | api.gopssl.com | `gopssl` (8001) | `/home/ubuntu/gopssl-backend` (`venv/`) | `.github/workflows/deploy-production.yml` |
| 베타 | `dev` | Oracle Cloud (OCI, Ubuntu) | OCI 내부 Docker Postgres 17 (127.0.0.1:5432) | dev-api.gopssl.com | `gopssl-beta` (8000) | `~/Gopssl-Backend` (`venv/`, Python 3.12) | `.github/workflows/deploy-beta.yml` |

- **main 머지 = 운영 배포, dev 머지 = 베타 배포.** 둘 다 머지 즉시 자동으로 실행된다.

---

## 자동 배포 흐름

```
PR 머지 (main 또는 dev 에 push)
  → GitHub Actions 트리거
  → 대상 서버 SSH 접속
  → venv/bin/pip 존재 확인 (없으면 여기서 중단, 서비스는 그대로)
  → git fetch origin && git checkout -B <브랜치> origin/<브랜치>
  → venv/bin/pip install -r requirements.txt
  → sudo systemctl restart <서비스>
  → 서버 안에서 curl http://127.0.0.1:<포트>/docs 헬스 체크 (30초 재시도, 실패 시 워크플로 실패)
```

- 같은 환경의 배포는 `concurrency`로 한 번에 하나만 실행된다 (다음 실행은 대기).
- 헬스 체크는 `/docs`로 앱 기동만 확인한다. DB 연결은 확인하지 않는다.
- 서버의 `.env`(untracked)는 배포로 바뀌지 않는다.

## 수동 배포

GitHub → Actions 탭 → 워크플로 선택 → **Run workflow**

- "Deploy to Production (Lightsail)": 항상 `main`을 배포한다.
- "Deploy to Beta (OCI)": 배포할 브랜치를 입력할 수 있다 (기본 `dev`).

## GitHub Secrets 목록

| Secret 키 | 쓰는 워크플로 | 대상 |
|-----------|---------------|------|
| `BETA_HOST` | deploy-production.yml | Lightsail 호스트 |
| `BETA_USER` | deploy-production.yml | Lightsail SSH 사용자 |
| `BETA_SSH_KEY` | deploy-production.yml | Lightsail SSH 개인키 |
| `OCI_SSH_HOST` | deploy-beta.yml | OCI 호스트 |
| `OCI_SSH_USER` | deploy-beta.yml | OCI SSH 사용자 |
| `OCI_SSH_KEY` | deploy-beta.yml | OCI SSH 개인키 |

> `BETA_*` 이름은 예전 구조의 흔적이다. `LIGHTSAIL_*`로 이름을 바꾸는 작업은 별도로 진행한다.

---

## 로컬 개발 서버 실행

```bash
cd Gopssl-Backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

## DB 마이그레이션

현재 Alembic 미사용 — `Base.metadata.create_all(bind=engine)`으로 테이블 자동 생성.
스키마 변경 시 직접 ALTER TABLE 또는 DB 재생성 필요.

> ⚠️ Alembic 도입 예정 시 `alembic init`, `env.py` 설정 후 사용.

---

## 주의사항

- `main` = 운영, `dev` = 베타. dev·main에 직접 push 금지, 항상 PR.
- `.env` 파일은 서버에만 존재, 절대 커밋 금지
- `requirements.txt` 변경은 배포 시 자동으로 설치된다 (`venv/bin/pip install -r requirements.txt`).
