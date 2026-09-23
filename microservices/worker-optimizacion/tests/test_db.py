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

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConnection:
    def __init__(self, rows):
        self._cursor = FakeCursor(rows)

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class FakeContext:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *exc):
        return False


def _fake_get_connection(rows):
    conn = FakeConnection(rows)

    def factory():
        return FakeContext(conn)

    factory.conn = conn
    return factory


def test_get_consumption_history_returns_daily_rows(monkeypatch):
    rows = [(date(2024, 1, 1), 120.5), (date(2024, 1, 2), 130.0)]
    monkeypatch.setattr(db, "get_connection", _fake_get_connection(rows))

    history = db.get_consumption_history(days=7, chamber_id=3)

    assert history == [
        {"date": date(2024, 1, 1), "consumption_kwh": 120.5},
        {"date": date(2024, 1, 2), "consumption_kwh": 130.0},
    ]


def test_get_consumption_history_handles_null_sum(monkeypatch):
    rows = [(date(2024, 1, 1), None)]
    monkeypatch.setattr(db, "get_connection", _fake_get_connection(rows))

    assert db.get_consumption_history() == [
        {"date": date(2024, 1, 1), "consumption_kwh": 0.0}
    ]


def test_get_consumption_history_returns_empty_without_db(monkeypatch):
    monkeypatch.setattr(db, "get_connection", lambda: FakeContext(None))

    assert db.get_consumption_history() == []


def test_get_consumption_history_uses_default_chamber_and_days(monkeypatch):
    factory = _fake_get_connection([(date(2024, 1, 1), 1.0)])
    monkeypatch.setattr(db, "get_connection", factory)

    db.get_consumption_history()

    _, params = factory.conn._cursor.executed[-1]
    assert params == (db.CHAMBER_ID, 7)


def test_get_consumption_history_rejects_non_positive_days():
    with pytest.raises(ValueError):
        db.get_consumption_history(days=0)
