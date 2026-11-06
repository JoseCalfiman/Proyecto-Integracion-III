import logging
from pathlib import Path

import price


def setup_function():
    price._last_quote = None


def _write_csv(tmp_path: Path, rows: list[tuple[str, float]]) -> Path:
    csv = tmp_path / "precio_cne.csv"
    body = "\n".join(f"{d},{p}" for d, p in rows)
    csv.write_text(f"fecha,precio_clp_kwh\n{body}\n", encoding="utf-8")
    return csv


def test_price_from_csv_returns_latest_price(tmp_path):
    csv = _write_csv(tmp_path, [("2024-01-01", 138.5), ("2024-05-01", 152.4)])
    assert price._price_from_csv(csv) == 152.4


def test_price_from_csv_orders_by_date(tmp_path):
    csv = _write_csv(tmp_path, [("2024-05-01", 999.0), ("2024-01-01", 138.5)])
    assert price._price_from_csv(csv) == 999.0


def test_price_from_csv_missing_file_returns_none(tmp_path):
    assert price._price_from_csv(tmp_path / "no_existe.csv") is None


def test_price_from_csv_without_price_column_returns_none(tmp_path):
    csv = tmp_path / "precio_cne.csv"
    csv.write_text("fecha,otra_columna\n2024-01-01,1\n", encoding="utf-8")
    assert price._price_from_csv(csv) is None


def test_get_current_price_uses_csv_when_db_unavailable(monkeypatch, tmp_path):
    csv = _write_csv(tmp_path, [("2024-05-01", 152.4)])
    monkeypatch.setattr(price, "_price_from_db", lambda: None)
    monkeypatch.setattr(price, "CSV_PATH", csv)
    assert price.get_current_price() == 152.4


def test_get_current_price_uses_latest_db_row(monkeypatch, tmp_path):
    monkeypatch.setattr(price, "CSV_PATH", tmp_path / "no_existe.csv")
    monkeypatch.setattr(
        price,
        "_price_from_db",
        lambda: {"id_price": 9, "price_kwh": 148.2},
    )

    quote = price.get_current_quote()

    assert quote == {"id_price": 9, "price_kwh": 148.2}
    assert price.get_current_price() == 148.2


def test_get_current_price_reuses_last_when_update_fails(monkeypatch, caplog):
    state = {"n": 0}

    def fake_db():
        state["n"] += 1
        if state["n"] == 1:
            return {"id_price": 4, "price_kwh": 151.75}
        return None

    monkeypatch.setattr(price, "_price_from_db", fake_db)
    monkeypatch.setattr(price, "CSV_PATH", Path("no_existe.csv"))

    assert price.get_current_price() == 151.75
    with caplog.at_level(logging.WARNING, logger="price"):
        assert price.get_current_price() == 151.75

    assert "reutiliza el ultimo precio" in caplog.text
    assert price._last_quote["id_price"] == 4


def test_get_current_price_without_source_returns_none(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(price, "_price_from_db", lambda: None)
    monkeypatch.setattr(price, "CSV_PATH", tmp_path / "no_existe.csv")

    with caplog.at_level(logging.WARNING, logger="price"):
        assert price.get_current_price() is None

    assert "no hay precio disponible" in caplog.text


def test_bundled_precio_cne_csv_is_readable():
    assert price._price_from_csv() == 152.40
