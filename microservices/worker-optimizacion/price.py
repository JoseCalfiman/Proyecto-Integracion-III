from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Precio de respaldo (CLP/kWh) si no hay BD ni CSV disponible.
DEFAULT_PRICE_CLP_KWH = float(os.getenv("PRECIO_CLP_KWH", "145.0"))

# Archivo CSV con precios CNE, ubicado junto a este modulo por defecto.
DEFAULT_CSV_PATH = Path(__file__).with_name("precio_cne.csv")
CSV_PATH = Path(os.getenv("PRECIO_CNE_CSV", str(DEFAULT_CSV_PATH)))

_PRICE_FIELDS = ("precio_clp_kwh", "price_clp_kwh", "precio", "price", "valor")
_DATE_FIELDS = ("ts", "fecha", "date", "timestamp")


def _price_from_db() -> float | None:
    try:
        from db import get_latest_price
    except ImportError:  # pragma: no cover - dependencia opcional
        return None
    return get_latest_price()


def _price_from_csv(path: Path = CSV_PATH) -> float | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        logger.warning("[price] no se pudo leer %s: %s", path, exc)
        return None

    price_col = next((c for c in _PRICE_FIELDS if c in df.columns), None)
    if price_col is None:
        logger.warning("[price] %s no tiene columna de precio reconocible", path)
        return None

    date_col = next((c for c in _DATE_FIELDS if c in df.columns), None)
    if date_col is not None:
        df = df.assign(**{date_col: pd.to_datetime(df[date_col], errors="coerce")})
        df = df.sort_values(date_col)

    prices = pd.to_numeric(df[price_col], errors="coerce").dropna()
    if prices.empty:
        return None
    return float(prices.iloc[-1])


def get_current_price() -> float:
    """Precio del kWh (CLP) desde ``energy_price``, luego CSV, luego respaldo."""
    price = _price_from_db()
    if price is not None:
        return price

    price = _price_from_csv()
    if price is not None:
        return price

    logger.info(
        "[price] usando precio de respaldo %.2f CLP/kWh", DEFAULT_PRICE_CLP_KWH
    )
    return DEFAULT_PRICE_CLP_KWH
