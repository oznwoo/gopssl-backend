"""
서버를 띄우지 않고 app.openapi()로 OpenAPI 스펙을 뽑아 docs/openapi.v1.json에 저장한다.

main.py는 import 시점에 Base.metadata.create_all(bind=engine)을 실행하므로 그냥 import하면
DATABASE_URL의 DB에 접속한다. 스펙 추출에는 DB가 필요 없으므로 아래처럼 DB 접속 자체를 없앤다.

- DATABASE_URL을 접속 불가능한 더미 값으로 덮어쓴다. load_dotenv()는 이미 있는 환경변수를
  덮어쓰지 않으므로 .env나 셸에 어떤 값이 있어도 이 더미 값이 쓰인다.
- main을 import하기 전에 MetaData.create_all을 no-op으로 바꾼다.

사용법 (레포 루트에서): python scripts/export_openapi.py
"""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "openapi.v1.json"

os.environ["DATABASE_URL"] = "postgresql+psycopg2://export:export@127.0.0.1:1/openapi_export_no_connect"
os.environ["SECRET_KEY"] = "openapi-export-dummy"

sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import MetaData  # noqa: E402

MetaData.create_all = lambda self, *args, **kwargs: None

from main import app  # noqa: E402


def main() -> None:
    spec = app.openapi()
    text = json.dumps(spec, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(text, encoding="utf-8")
    print(f"{OUTPUT_PATH.relative_to(REPO_ROOT)}: 경로 {len(spec['paths'])}개, OpenAPI {spec['openapi']}")


if __name__ == "__main__":
    main()
