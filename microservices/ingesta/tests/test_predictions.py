"""Consultas y contrato de predicciones, sin PostgreSQL ni workers externos."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from uuid import UUID

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import Chamber, Prediction
from routes.predictions import latest_prediction, prediction_history, router
from schemas import PredictionRead


class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Chamber.__table__.create(self.engine)
        Prediction.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.a = UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        self.b = UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
        self.empty = UUID('cccccccc-cccc-cccc-cccc-cccccccccccc')
        self.db.add_all([Chamber(id_chamber=c) for c in (self.a, self.b, self.empty)])
        for identifier, chamber, day in [(10, self.a, 1), (2, self.a, 2), (3, self.a, 2), (20, self.b, 3)]:
            self.db.add(Prediction(id_prediction=identifier, id_chamber=chamber,
                calculated_slope=Decimal('0.1234'), projected_temperature=Decimal('-12.50'),
                remaining_time_min=Decimal('42.25'), risk_level='ALTO',
                calculation_date=datetime(2026, 11, day, tzinfo=timezone.utc)))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_latest_uses_date_then_id_and_isolates_chamber(self):
        self.assertEqual(latest_prediction(self.a, self.db).id_prediction, 3)
        self.assertEqual(latest_prediction(self.b, self.db).id_prediction, 20)

    def test_history_order_and_pagination(self):
        rows = prediction_history(self.a, limit=100, offset=0, db=self.db)
        self.assertEqual([r.id_prediction for r in rows], [3, 2, 10])
        page = prediction_history(self.a, limit=1, offset=1, db=self.db)
        self.assertEqual([r.id_prediction for r in page], [2])
        self.assertEqual(prediction_history(self.a, limit=10, offset=99, db=self.db), [])

    def test_response_maps_slope_and_serializes_numbers(self):
        row = latest_prediction(self.a, self.db)
        payload = PredictionRead.model_validate(row).model_dump(mode='json', by_alias=True)
        self.assertEqual(payload['slope'], 0.1234)
        self.assertNotIn('calculated_slope', payload)
        self.assertEqual(payload['projected_temperature'], -12.5)
        self.assertEqual(payload['remaining_time_min'], 42.25)
        self.assertEqual(payload['risk_level'], 'ALTO')
        self.assertEqual(payload['id_chamber'], str(self.a))
        self.assertTrue(payload['calculation_date'].startswith('2026-11-02T'))
        row.calculated_slope = row.projected_temperature = row.remaining_time_min = None
        payload = PredictionRead.model_validate(row).model_dump(mode='json')
        self.assertIsNone(payload['slope'])
        self.assertIsNone(payload['remaining_time_min'])

    def test_no_predictions_and_unknown_chamber(self):
        self.assertEqual(prediction_history(self.empty, limit=100, offset=0, db=self.db), [])
        with self.assertRaises(HTTPException) as error:
            latest_prediction(self.empty, self.db)
        self.assertEqual(error.exception.status_code, 404)
        unknown = UUID('dddddddd-dddd-dddd-dddd-dddddddddddd')
        for call in (lambda: latest_prediction(unknown, self.db),
                     lambda: prediction_history(unknown, limit=100, offset=0, db=self.db)):
            with self.assertRaises(HTTPException) as error:
                call()
            self.assertEqual(error.exception.detail, 'Cámara no encontrada')

    def test_openapi_routes_and_query_validation(self):
        app = FastAPI()
        app.include_router(router, prefix='/api/v1')
        paths = app.openapi()['paths']
        self.assertEqual(set(paths), {'/api/v1/predictions/latest', '/api/v1/predictions/history'})
        operation = paths['/api/v1/predictions/history']['get']
        params = {p['name']: p for p in operation['parameters']}
        self.assertTrue(params['id_chamber']['required'])
        self.assertEqual(params['id_chamber']['schema']['format'], 'uuid')
        self.assertEqual(params['limit']['schema']['maximum'], 1000)
        self.assertEqual(params['limit']['schema']['minimum'], 1)
        self.assertEqual(params['offset']['schema']['minimum'], 0)


if __name__ == '__main__':
    unittest.main()
