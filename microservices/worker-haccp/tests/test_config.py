import pytest
from sqlalchemy.engine import URL

from config import get_database_url


def test_database_url_takes_precedence_over_db_settings():
    configured_url = "postgresql+psycopg2://user:password@db:5432/frigorifico"

    result = get_database_url(
        {
            "DATABASE_URL": configured_url,
            "DB_HOST": "ignored",
            "DB_PORT": "5432",
            "DB_NAME": "ignored",
            "DB_USER": "ignored",
            "DB_PASSWORD": "ignored",
        }
    )

    assert result == configured_url


@pytest.mark.parametrize(
    "configured_url",
    [
        "postgresql://user:password@db:5432/frigorifico",
        "postgresql+psycopg2://user:password@db:5432/frigorifico",
    ],
)
def test_database_url_accepts_postgresql_schemes(configured_url):
    assert get_database_url({"DATABASE_URL": configured_url}) == configured_url


@pytest.mark.parametrize(
    "configured_url",
    [
        "sqlite:///worker.db",
        "mysql+pymysql://user:password@db/frigorifico",
        "postgresql+psycopg://user:password@db/frigorifico",
    ],
)
def test_database_url_rejects_unsupported_engines_and_drivers(configured_url):
    with pytest.raises(RuntimeError, match="must use PostgreSQL"):
        get_database_url({"DATABASE_URL": configured_url})


def test_database_url_rejects_malformed_url():
    with pytest.raises(RuntimeError, match="not a valid SQLAlchemy URL"):
        get_database_url({"DATABASE_URL": "://invalid"})


def test_db_settings_create_url_with_escaped_credentials():
    result = get_database_url(
        {
            "DB_HOST": "timescaledb",
            "DB_PORT": "5432",
            "DB_NAME": "frigorifico",
            "DB_USER": "worker@service",
            "DB_PASSWORD": "p@ss:word/with?symbols#",
        }
    )

    assert isinstance(result, URL)
    assert result.password == "p@ss:word/with?symbols#"
    assert (
        result.render_as_string(hide_password=False)
        == "postgresql+psycopg2://worker%40service:p%40ss%3Aword%2Fwith%3Fsymbols%23"
        "@timescaledb:5432/frigorifico"
    )


def test_missing_database_settings_raise_clear_error():
    with pytest.raises(RuntimeError, match="Set DATABASE_URL or all"):
        get_database_url({})


def test_invalid_db_port_raises_clear_error():
    with pytest.raises(RuntimeError, match="DB_PORT must be a valid integer"):
        get_database_url(
            {
                "DB_HOST": "timescaledb",
                "DB_PORT": "invalid",
                "DB_NAME": "frigorifico",
                "DB_USER": "worker",
                "DB_PASSWORD": "secret",
            }
        )
