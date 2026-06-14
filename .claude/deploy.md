# 배포 가이드

## 인프라

- **서버**: Oracle Cloud Infrastructure (OCI) — Ubuntu
- **서비스**: systemd (`gopssl.service`)
- **CI/CD**: GitHub Actions (`dev` 브랜치 push → 자동 배포)

---

## 자동 배포 흐름

```
로컬에서 dev 브랜치 push
  → GitHub Actions 트리거 (.github/workflows/deploy.yml)
  → OCI 서버 SSH 접속
  → git pull origin dev
  → sudo systemctl restart gopssl.service
```

## GitHub Secrets 목록

| Secret 키 | 설명 |
|-----------|------|
| `OCI_SSH_HOST` | OCI 서버 IP |
| `OCI_SSH_USER` | SSH 사용자명 |
| `OCI_SSH_KEY` | SSH 개인키 |

---

## 수동 배포 (긴급 시)

```bash
ssh <user>@<OCI_HOST>
cd Gopssl-Backend
git pull origin dev
sudo systemctl restart gopssl.service
sudo systemctl status gopssl.service
```

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

- `dev` 브랜치가 운영 브랜치임 (main이 아님)
- `.env` 파일은 서버에만 존재, 절대 커밋 금지
- `requirements.txt` 변경 시 서버에서 수동으로 `pip install -r requirements.txt` 필요
