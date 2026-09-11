import os

os.environ.setdefault(
    "RESOLVEAI_DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/resolveai_test",
)
os.environ.setdefault("RESOLVEAI_SESSION_COOKIE_SECURE", "false")
