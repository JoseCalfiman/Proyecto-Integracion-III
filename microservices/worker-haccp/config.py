import os
from collections.abc import Mapping

from sqlalchemy.exc import ArgumentError
from sqlalchemy.engine import URL, make_url

POSTGRESQL_DRIVERS = {"postgresql", "postgresql+psycopg2"}


def get_database_url(environment: Mapping[str, str] | None = None) -> str | URL:
    """Return the configured PostgreSQL URL or build one from DB_* settings."""
    env = os.environ if environment is None else environment
    database_url = env.get("DATABASE_URL")
    if database_url and database_url.strip():
        try:
            parsed_url = make_url(database_url)
        except ArgumentError as exc:
            raise RuntimeError("DATABASE_URL is not a valid SQLAlchemy URL.") from exc
        if parsed_url.drivername not in POSTGRESQL_DRIVERS:
            raise RuntimeError(
                "DATABASE_URL must use PostgreSQL with the installed psycopg2 driver "
                "(postgresql:// or postgresql+psycopg2://)."
            )
        return database_url

    required_settings = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing_settings = [
        setting for setting in required_settings
        if not env.get(setting) or not env[setting].strip()
    ]
    if missing_settings:
        missing = ", ".join(missing_settings)
        raise RuntimeError(
            "Database configuration is missing. Set DATABASE_URL or all of "
            f"the following settings: {missing}."
        )

    try:
        port = int(env["DB_PORT"])
    except ValueError as exc:
        raise RuntimeError("DB_PORT must be a valid integer.") from exc

    return URL.create(
        "postgresql+psycopg2",
        username=env["DB_USER"],
        password=env["DB_PASSWORD"],
        host=env["DB_HOST"],
        port=port,
        database=env["DB_NAME"],
    )