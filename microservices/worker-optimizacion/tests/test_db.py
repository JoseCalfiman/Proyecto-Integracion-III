from datetime import date

import pytest

import db


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def executemany(self, sql, seq_of_params=None):
        self.executed.append((sql, seq_of_params))

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConnection:
    def __init__(self, rows):
        self._cursor = FakeCursor(rows)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class FakeContext:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *exc):
        return False


def test_dsn_uses_db_password(monkeypatch):
    monkeypatch.setattr(db, "DB_PASSWORD", "secret-from-db-password")

    assert db._dsn_kwargs()["password"] == "secret-from-db-password"


def test_connection_rolls_back_and_propagates_transaction_errors(monkeypatch):
    import db

    connection = FakeConnection([])
    monkeypatch.setattr(
        db,
        "psycopg2",
        type("Psycopg", (), {"connect": staticmethod(lambda **kwargs: connection)}),
    )

    with pytest.raises(RuntimeError, match="fallo SQL"):
        with db.get_connection():
            raise RuntimeError("fallo SQL")

    assert connection.rolled_back is True
    assert connection.committed is False


def _fake_get_connection(rows):
    conn = FakeConnection(rows)

    def factory():
        return FakeContext(conn)

    factory.conn = conn
    return factory


def test_get_latest_energy_price_reads_latest_row(monkeypatch):
    factory = _fake_get_connection([(9, 148.2)])
    monkeypatch.setattr(db, "get_connection", factory)

    assert db.get_latest_energy_price() == {"id_price": 9, "price_kwh": 148.2}
    sql, params = factory.conn._cursor.executed[-1]
    assert "id_price" in sql
    assert "price_kwh" in sql
    assert "queried_at" in sql
    assert "FROM energy_price" in sql
    assert "price_id" not in sql
    assert params is None


def test_validate_schema_checks_official_columns_and_chamber_uuid(monkeypatch):
    factory = _fake_get_connection([(1,)])
    monkeypatch.setattr(db, "get_connection", factory)
    chamber_id = "44444444-4444-4444-4444-444444444444"

    assert db.validate_schema(chamber_id) is True

    statements = [sql for sql, _ in factory.conn._cursor.executed]
    assert any("timestamp, id_chamber, consumption_kw" in sql for sql in statements)
    assert any("id_price, price_kwh, queried_at" in sql for sql in statements)
    assert any("FROM predicted_consumption" in sql for sql in statements)
    assert any("FROM saving_recommendation" in sql for sql in statements)
    assert any("WHERE id_chamber = %s" in sql for sql in statements)
    assert factory.conn._cursor.executed[-1][1] == (chamber_id,)


def test_validate_schema_fails_when_database_is_unavailable(monkeypatch):
    monkeypatch.setattr(db, "get_connection", lambda: FakeContext(None))

    assert db.validate_schema() is False


def test_get_latest_energy_price_empty_or_without_db(monkeypatch):
    monkeypatch.setattr(db, "get_connection", _fake_get_connection([]))
    assert db.get_latest_energy_price() is None

    monkeypatch.setattr(db, "get_connection", lambda: FakeContext(None))
    assert db.get_latest_energy_price() is None
    assert db.get_latest_price() is None
    assert db.get_latest_price_id() is None


def test_get_consumption_history_returns_daily_rows(monkeypatch):
    rows = [(date(2024, 1, 1), 120.5), (date(2024, 1, 2), 130.0)]
    id_chamber = "44444444-4444-4444-4444-444444444444"
    factory = _fake_get_connection(rows)
    monkeypatch.setattr(db, "get_connection", factory)

    history = db.get_consumption_history(days=7, id_chamber=id_chamber)

    assert history == [
        {"date": date(2024, 1, 1), "consumption_kwh": 120.5},
        {"date": date(2024, 1, 2), "consumption_kwh": 130.0},
    ]
    sql, params = factory.conn._cursor.executed[-1]
    assert "SUM(consumption_kw * 10.0 / 3600.0)" in sql
    assert "date_trunc('day', timestamp)" in sql
    assert "FROM sensor_data" in sql
    assert "id_chamber = %s" in sql
    assert "GROUP BY day" in sql
    assert params == (id_chamber, 7)


def test_get_consumption_history_handles_null_sum(monkeypatch):
    rows = [(date(2024, 1, 1), None)]
    monkeypatch.setattr(db, "get_connection", _fake_get_connection(rows))

    assert db.get_consumption_history() == [
        {"date": date(2024, 1, 1), "consumption_kwh": 0.0}
    ]


def test_get_consumption_history_returns_empty_without_db(monkeypatch):
    monkeypatch.setattr(db, "get_connection", lambda: FakeContext(None))

    assert db.get_consumption_history() == []


def test_get_consumption_history_uses_default_uuid_chamber_and_days(monkeypatch):
    factory = _fake_get_connection([(date(2024, 1, 1), 1.0)])
    monkeypatch.setattr(db, "get_connection", factory)

    db.get_consumption_history()

    _, params = factory.conn._cursor.executed[-1]
    assert params == ("44444444-4444-4444-4444-444444444444", 7)


def test_get_consumption_history_rejects_non_uuid_chamber():
    with pytest.raises(ValueError, match="UUID"):
        db.get_consumption_history(id_chamber="3")


def test_get_consumption_history_rejects_non_positive_days():
    with pytest.raises(ValueError):
        db.get_consumption_history(days=0)


def test_save_predicted_consumption_uses_official_chamber_column(monkeypatch):
    factory = _fake_get_connection([])
    monkeypatch.setattr(db, "get_connection", factory)

    assert db.save_predicted_consumption(
        target_date="2024-01-08",
        predicted_kwh=42.5,
        id_chamber="44444444-4444-4444-4444-444444444444",
    ) is True

    sql, params = factory.conn._cursor.executed[-1]
    assert "INSERT INTO predicted_consumption" in sql
    assert "(id_chamber, prediction_date, predicted_consumption_kw)" in sql
    assert "chamber_id" not in sql
    assert params == ("44444444-4444-4444-4444-444444444444", "2024-01-08", 42.5)


def test_save_saving_recommendations_inserts_savings_percentage(monkeypatch):
    factory = _fake_get_connection([])
    monkeypatch.setattr(db, "get_connection", factory)

    ok = db.save_saving_recommendations(
        target_date="2024-01-08",
        price_clp_kwh=145.0,
        recommendations=[
            {
                "action": "apagar",
                "estimated_savings": 1450.0,
                "savings_percentage": 1.72,
                "equipment": "camaras_2_y_3",
                "window": ["18:00", "22:00"],
                "hours": 2,
            }
        ],
        id_price=5,
        id_chamber="44444444-4444-4444-4444-444444444444",
    )

    assert ok is True
    sql, params = factory.conn._cursor.executed[-1]
    assert "INSERT INTO saving_recommendation" in sql
    assert "expected_saving_pct" in sql
    assert "expected_saving_amount" in sql
    assert "rationale" in sql
    assert "saving_recommendations" not in sql
    assert "company_id" not in sql
    (
        id_chamber,
        id_price,
        action,
        savings_percentage,
        amount,
        rationale,
        status,
    ) = params[0]
    assert (id_chamber, id_price, action) == (
        "44444444-4444-4444-4444-444444444444",
        5,
        "apagar",
    )
    assert savings_percentage == 1.72
    assert amount == 1450.0
    assert status == "pending"
    assert "target_date" in rationale


def test_save_saving_recommendations_without_rows_is_noop(monkeypatch):
    def fail():
        raise AssertionError("no deberia conectar a la BD")

    monkeypatch.setattr(db, "get_connection", fail)
    assert db.save_saving_recommendations(
        target_date="2024-01-08", price_clp_kwh=145.0, recommendations=[]
    ) is True


def test_save_report_accepts_optimization_reports_wire_fields(monkeypatch):
    chamber_id = "44444444-4444-4444-4444-444444444444"
    saved_predictions = []
    saved_recommendations = []
    monkeypatch.setattr(
        db,
        "save_predicted_consumption",
        lambda **kwargs: saved_predictions.append(kwargs) or True,
    )
    monkeypatch.setattr(
        db,
        "save_saving_recommendations",
        lambda **kwargs: saved_recommendations.append(kwargs) or True,
    )

    assert db.save_report(
        {
            "id_chamber": chamber_id,
            "prediction_date": "2026-10-26",
            "predicted_kwh": 580.0,
            "price_kwh": 145.5,
            "id_price": 1,
            "recommendations": [{"action": "apagar"}],
        }
    ) is True

    assert saved_predictions == [
        {
            "target_date": "2026-10-26",
            "predicted_kwh": 580.0,
            "id_chamber": chamber_id,
        }
    ]
    assert saved_recommendations == [
        {
            "target_date": "2026-10-26",
            "price_clp_kwh": 145.5,
            "recommendations": [{"action": "apagar"}],
            "id_price": 1,
            "id_chamber": chamber_id,
        }
    ]
