from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Archivo CSV con precios CNE, ubicado junto a este modulo por defecto.
DEFAULT_CSV_PATH = Path(__file__).with_name("precio_cne.csv")
CSV_PATH = Path(os.getenv("PRECIO_CNE_CSV", str(DEFAULT_CSV_PATH)))

_PRICE_FIELDS = ("precio_clp_kwh", "price_clp_kwh", "precio", "price", "valor")
_DATE_FIELDS = ("ts", "fecha", "date", "timestamp")

# Ultima lectura exitosa. Se reutiliza si falla la actualizacion.
_last_quote: dict[str, float | int | None] | None = None


def _price_from_db() -> dict[str, float | int] | None:
    try:
        from db import get_latest_energy_price
    except ImportError:  # pragma: no cover - dependencia opcional
        return None
    return get_latest_energy_price()


def _price_from_csv(path: Path | None = None) -> float | None:
    """Ultimo precio (CLP/kWh) del CSV local ``precio_cne.csv`` o ``None``.

    El archivo debe tener el formato ``fecha,precio_clp_kwh``. Si ``path`` es
    ``None`` se usa ``CSV_PATH`` (configurable con ``PRECIO_CNE_CSV``).
    """
    path = Path(path) if path is not None else CSV_PATH
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


def get_current_quote() -> dict[str, float | int | None] | None:
    """Ultimo precio de ``energy_price``.

    Si la lectura falla y ya habia un precio, lo reutiliza y deja un WARNING.
    No usa un valor escrito a mano en el codigo.
    """
    global _last_quote

    quote: dict[str, float | int] | None = None
    try:
        quote = _price_from_db()
    except Exception as exc:  # noqa: BLE001 - cualquier fallo de lectura se degrada
        logger.warning("[price] fallo al leer energy_price: %s", exc)
        quote = None

    if quote is not None:
        _last_quote = {
            "id_price": quote["id_price"],
            "price_kwh": float(quote["price_kwh"]),
        }
        return _last_quote

    if _last_quote is not None:
        logger.warning(
            "[price] fallo la actualizacion de energy_price; "
            "se reutiliza el ultimo precio %.4f CLP/kWh (id_price=%s)",
            _last_quote["price_kwh"],
            _last_quote["id_price"],
        )
        return _last_quote

    csv_price = _price_from_csv()
    if csv_price is not None:
        logger.warning(
            "[price] energy_price no disponible; se usa el ultimo precio del CSV %.4f CLP/kWh",
            csv_price,
        )
        _last_quote = {"id_price": None, "price_kwh": csv_price}
        return _last_quote

    logger.warning("[price] no hay precio disponible en energy_price")
    return None


def get_current_price() -> float | None:
    """Precio del kWh (CLP) desde ``energy_price`` o el ultimo valor conocido."""
    quote = get_current_quote()
    if quote is None:
        return None
    return float(quote["price_kwh"])
