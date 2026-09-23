from pathlib import Path

import price


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


def test_get_current_price_falls_back_to_default(monkeypatch, tmp_path):
    monkeypatch.setattr(price, "_price_from_db", lambda: None)
    monkeypatch.setattr(price, "CSV_PATH", tmp_path / "no_existe.csv")
    assert price.get_current_price() == price.DEFAULT_PRICE_CLP_KWH


def test_bundled_precio_cne_csv_is_readable():
    assert price._price_from_csv() == 152.40
