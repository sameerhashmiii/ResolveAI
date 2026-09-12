import asyncio
import json
import sys
from dataclasses import asdict

from app.config import get_settings
from app.db.session import session_factory
from app.demo.ingestion import OperationalIngestionService


async def _run() -> None:
    settings = get_settings()
    async with session_factory() as session:
        report = await OperationalIngestionService(session, settings.operational_data_dir).ingest()
    print(json.dumps(asdict(report), sort_keys=True))


def main() -> int:
    try:
        asyncio.run(_run())
    except Exception as exc:
        print(f"Operational ingestion failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
