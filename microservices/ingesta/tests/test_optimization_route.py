"""Contrato API de ahorro basado en recomendaciones persistidas."""

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

INGESTA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INGESTA))

fake_database = ModuleType("database")
fake_database.get_db = lambda: None
fake_models = ModuleType("models")
fake_models.SavingRecommendation = type(
    "SavingRecommendation",
    (),
    {
        "created_at": MagicMock(),
        "status": MagicMock(),
        "id_recommendation": MagicMock(),
    },
)
with patch.dict(sys.modules, {"database": fake_database, "models": fake_models}):
    spec = importlib.util.spec_from_file_location(
        "ingesta_optimization_route_test", INGESTA / "routes" / "optimization.py"
    )
    optimization_route = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(optimization_route)
    list_saving_recommendations = optimization_route.list_saving_recommendations


def test_recommendations_api_returns_clp_amount_and_action_from_latest_run():
    generated_at = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)
    recommendation = SimpleNamespace(
        id_recommendation=31,
        action="apagar",
        expected_saving_pct=12.5,
        expected_saving_amount=1450.0,
        rationale=(
            '{"target_date":"2026-10-29","equipment":"camaras_2_y_3",'
            '"window":["18:00","22:00"],"hours":2}'
        ),
        status="pending",
        created_at=generated_at,
    )
    latest_query = MagicMock()
    latest_query.filter.return_value.scalar.return_value = generated_at
    records_query = MagicMock()
    records_query.filter.return_value.order_by.return_value.all.return_value = [
        recommendation
    ]
    db = MagicMock()
    db.query.side_effect = [latest_query, records_query]

    results = list_saving_recommendations(db)

    assert len(results) == 1
    result = results[0]
    assert result["monto_clp"] == 1450.0
    assert result["porcentaje_ahorro"] == 12.5
    assert result["titulo"] == "Apagar Cámaras 2 y 3"
    assert "18:00–22:00" in result["descripcion"]
    assert "2026-10-29" in result["descripcion"]
    assert result["status"] == "pending"
    response_item = optimization_route.SavingRecommendationRead.model_validate(result)
    assert response_item.model_dump()["monto_clp"] == 1450.0


def test_recommendations_api_returns_empty_when_no_pending_run_exists():
    query = MagicMock()
    query.filter.return_value.scalar.return_value = None
    db = MagicMock()
    db.query.return_value = query

    assert list_saving_recommendations(db) == []
    db.query.assert_called_once()
