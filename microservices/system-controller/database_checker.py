import os

from health_checker import CheckResult, check_tcp


async def check() -> CheckResult:
    host = os.getenv("PGHOST") or os.getenv("DB_HOST", "timescaledb-service")
    port = int(os.getenv("PGPORT") or os.getenv("DB_PORT", "5432"))
    return await check_tcp(host, port, timeout=3.0)
