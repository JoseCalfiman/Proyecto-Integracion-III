"""Pruebas focalizadas de consultas y contratos de optimización, sin servicios externos."""
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import PredictedConsumption, SavingRecommendation
from routes.optimizacion import forecast, recommendations, router


class OptimizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        SavingRecommendation.__table__.create(self.engine)
        PredictedConsumption.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.a = UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        self.b = UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_recommendations_map_saved_fields_and_only_pending(self):
        for identifier, chamber, status in [(1, self.a, 'pending'), (2, self.b, 'pending'), (3, self.a, 'applied')]:
            self.db.add(SavingRecommendation(
                id_recommendation=identifier, id_chamber=chamber, status=status,
                action='Ajustar setpoint', rationale='Horario valle',
                expected_saving_pct=Decimal('12.500'), expected_saving_amount=Decimal('45000.25'),
                created_at=datetime(2026, 11, 1)))
        self.db.commit()
        rows = recommendations(db=self.db)
        self.assertEqual([r.id for r in rows], [2, 1])
        row = recommendations(id_chamber=self.a, db=self.db)[0].model_dump(mode='json')
        self.assertEqual(row['titulo'], 'Ajustar setpoint')
        self.assertEqual(row['descripcion'], 'Horario valle')
        self.assertEqual(row['porcentaje_ahorro'], 12.5)
        self.assertEqual(row['monto_clp'], 45000.25)
        self.assertEqual(row['id_chamber'], str(self.a))

    def test_forecast_groups_by_date_and_filters_chamber(self):
        for identifier, chamber, day, value in [(1, self.a, 2, 100), (2, self.b, 2, 50), (3, self.a, 1, 80)]:
            self.db.add(PredictedConsumption(id_consumption_prediction=identifier,
                id_chamber=chamber, prediction_date=date(2026, 11, day), predicted_consumption_kw=value))
        self.db.commit()
        rows = forecast(db=self.db)
        self.assertEqual([r.model_dump(mode='json') for r in rows], [
            {'date': '2026-11-01', 'pronostico': 80.0, 'historico': None},
            {'date': '2026-11-02', 'pronostico': 150.0, 'historico': None}])
        self.assertEqual(forecast(id_chamber=self.a, db=self.db)[1].pronostico, 100)

    def test_empty_tables_and_nullable_values(self):
        self.assertEqual(recommendations(db=self.db), [])
        self.assertEqual(forecast(db=self.db), [])
        self.db.add(SavingRecommendation(id_recommendation=1, status='pending'))
        self.db.add(PredictedConsumption(id_consumption_prediction=1,
            prediction_date=date(2026, 11, 1)))
        self.db.commit()
        self.assertIsNone(recommendations(db=self.db)[0].monto_clp)
        self.assertIsNone(forecast(db=self.db)[0].pronostico)

    def test_get_route_names(self):
        self.assertEqual({r.path for r in router.routes}, {
            '/optimizacion/recommendations', '/optimizacion/forecast'})
        self.assertTrue(all(r.methods == {'GET'} for r in router.routes))


if __name__ == '__main__':
    unittest.main()
