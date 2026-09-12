"""Export the FastAPI schema without connecting to a database."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT = ROOT / "docs" / "openapi.json"
DATABASE_URL = "postgresql+asyncpg://openapi:openapi@127.0.0.1:1/openapi"

os.environ["RESOLVEAI_DATABASE_URL"] = DATABASE_URL
sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> None:
    settings = Settings(
        app_name="ResolveAI",
        app_version=str(Settings.model_fields["app_version"].default),
        database_url=DATABASE_URL,
        environment="test",
        session_cookie_secure=False,
        trusted_hosts=["localhost"],
    )
    schema = create_app(settings).openapi()
    rendered = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Exported {len(schema['paths'])} paths to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
