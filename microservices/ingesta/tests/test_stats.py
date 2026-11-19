"""Contrato HTTP de estadísticas con una base SQLite aislada, sin servicios externos."""
import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys
import unittest
from urllib.parse import urlencode
from uuid import UUID

from fastapi import FastAPI
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import get_db
from models import Chamber, GeneratedAlert, SavingRecommendation, SensorData
from routes.stats import router


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        metadata = MetaData()
        for table in SensorData.metadata.tables.values():
            table.to_metadata(metadata)
        metadata.tables["sensor_data"].c.id_data.autoincrement = False
        metadata.tables["sensor_data"].create(self.engine)
        self.db = Session(self.engine)
        self.chamber = UUID("55555555-5555-5555-5555-555555555555")
        for identifier, chamber, timestamp, temperature, power in [
            (1, self.chamber, '2026-10-24T00:00:00', -20, 1),
            (2, self.chamber, '2026-10-24T12:00:00', -18, 2),
            (3, self.chamber, '2026-10-24T23:59:59', -16, 3),
            (4, self.chamber, '2026-10-25T00:00:00', -14, 4),
            (5, self.chamber, '2026-10-25T12:00:00', None, 5),
            (6, UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), '2026-10-24T12:00:00', 50, 99),
        ]:
            self.db.add(SensorData(id_data=identifier, id_chamber=chamber,
                                   timestamp=datetime.fromisoformat(timestamp),
                                   temperature=temperature, consumption_kw=power))
        self.db.commit()
        self.app = FastAPI()
        self.app.include_router(router, prefix='/api/v1')
        self.app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def request(self, **changes):
        params = dict(id_chamber=str(self.chamber), desde='2026-10-24', hasta='2026-10-24')
        params.update(changes)
        params = {key: value for key, value in params.items() if value is not None}
        chamber = params.pop('id_chamber', str(self.chamber))
        path = getattr(self, 'endpoint', '/api/v1/stats/chambers/' + chamber)
        messages = []

        async def run():
            async def receive():
                return {'type': 'http.request', 'body': b'', 'more_body': False}

            async def send(message):
                messages.append(message)

            await self.app({'type': 'http', 'asgi': {'version': '3.0'},
                            'http_version': '1.1', 'method': 'GET', 'scheme': 'http',
                            'path': path, 'raw_path': path.encode(),
                            'query_string': urlencode(params).encode(), 'headers': [],
                            'server': ('test', 80), 'client': ('test', 1)}, receive, send)
        asyncio.run(run())
        return messages[0]['status'], json.loads(b''.join(m.get('body', b'') for m in messages[1:]))

    def assert_stats(self, actual, expected):
        keys = ['n', 'media', 'mediana', 'minimo', 'maximo',
                'desviacion_estandar', 'q1', 'q3', 'iqr']
        self.assertEqual(set(actual), set(keys))
        for key, value in zip(keys, expected):
            self.assertAlmostEqual(actual[key], value, places=10, msg=key)

    def test_two_ranges_against_manual_calculation(self):
        # Día 24: T=[-20,-18,-16], suma cuadrados centrados=8.
        status, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(body['id_chamber'], str(self.chamber))
        self.assert_stats(body['temperature'], [3,-18,-18,-20,-16,(8/3)**0.5,-19,-17,2])
        self.assert_stats(body['consumption_kw'], [3,2,2,1,3,(2/3)**0.5,1.5,2.5,1])
        # Días 24-25: T=[-20,-18,-16,-14], C=[1,2,3,4,5].
        status, body = self.request(hasta='2026-10-25')
        self.assertEqual(status, 200)
        self.assert_stats(body['temperature'], [4,-17,-17,-20,-14,5**0.5,-18.5,-15.5,3])
        self.assert_stats(body['consumption_kw'], [5,3,3,1,5,2**0.5,2,4,2])

    def test_singleton_and_timezone_inclusive(self):
        status, body = self.request(desde='2026-10-23T21:00:00-03:00', hasta='2026-10-24T00:00:00Z')
        self.assertEqual(status, 200)
        self.assert_stats(body['temperature'], [1,-20,-20,-20,-20,0,-20,-20,0])

    def test_empty_and_null_variable(self):
        for changes in [dict(desde='2026-10-26', hasta='2026-10-26'),
                        dict(id_chamber='cccccccc-cccc-cccc-cccc-cccccccccccc')]:
            status, body = self.request(**changes)
            self.assertEqual(status, 200)
            for name in ['temperature', 'consumption_kw']:
                self.assertEqual(body[name]['n'], 0)
                self.assertTrue(all(v is None for k,v in body[name].items() if k != 'n'))
        status, body = self.request(desde='2026-10-25T12:00:00Z', hasta='2026-10-25T12:00:00Z')
        self.assertEqual(status, 200)
        self.assertEqual(body['temperature']['n'], 0)
        self.assertEqual(body['consumption_kw']['n'], 1)

    def test_invalid_filters(self):
        for changes in [dict(id_chamber='invalid'), dict(desde=None), dict(hasta=None),
                        dict(desde='bad'), dict(hasta='2026-02-30'),
                        dict(desde='2026-10-25', hasta='2026-10-24')]:
            with self.subTest(changes=changes):
                self.assertEqual(self.request(**changes)[0], 422)


class SummaryTests(StatsTests):
    endpoint = '/api/v1/stats/summary'

    def setUp(self):
        super().setUp()
        for model in (Chamber, GeneratedAlert, SavingRecommendation):
            model.__table__.create(self.engine)
        self.db.query(SensorData).delete()
        self.ids = [UUID(f"aaaaaaaa-aaaa-4aaa-8aaa-{i:012d}") for i in range(1, 12)]
        for i, chamber in enumerate(self.ids, 1):
            self.db.add(Chamber(id_chamber=chamber, name=f'Cámara {i}', active=i <= 10))
            # Cámara 10 sin lecturas; cámara 11 inactiva con valores altos.
            if i != 10:
                for j, power in enumerate((i, i + 2)):
                    self.db.add(SensorData(id_data=i*10+j, id_chamber=chamber,
                        timestamp=datetime(2026, 10, 24, 12+j),
                        temperature=-20+2*j, consumption_kw=power))
            for j in range(i):
                self.db.add(GeneratedAlert(id_alert=i*100+j, id_chamber=chamber,
                    severity='critical' if j == 0 else 'medium', status='resolved',
                    generation_date=datetime(2026, 10, 24, 12)))
            for j, status in enumerate(('pending', 'applied', 'pending')):
                self.db.add(SavingRecommendation(id_recommendation=i*10+j,
                    id_chamber=chamber, status=status,
                    created_at=datetime(2026, 10, 24 if j < 2 else 25)))
        self.db.commit()

    def test_two_ranges_against_manual_calculation(self):
        status, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(len(body['chambers']), 10)
        for i, row in enumerate(body['chambers'], 1):
            self.assertEqual(row['id_chamber'], str(self.ids[i-1]))
            self.assertEqual(row['alerts'], i)
            self.assertEqual(row['critical_alerts'], 1)
            self.assertEqual(row['pending_recommendations'], 1)
            if i < 10:
                self.assertEqual(row['temperature']['media'], -19)
                self.assertEqual(row['temperature']['mediana'], -19)
                self.assertEqual(row['temperature']['desviacion_estandar'], 1)
                self.assertEqual(row['consumption_kw']['media'], i+1)
                self.assertEqual(row['consumption_total_kw'], 2*i+2)
            else:
                self.assertIsNone(row['consumption_total_kw'])
        ranks = body['rankings']
        self.assertEqual([r['id_chamber'] for r in ranks['top_alerts']],
                         [str(c) for c in reversed(self.ids[:10])])
        self.assertEqual([r['value'] for r in ranks['top_consumption']], list(range(20, 3, -2)))
        self.assertEqual([r['id_chamber'] for r in ranks['top_consumption']],
                         [str(c) for c in reversed(self.ids[:9])])
        self.assertEqual(self.request(hasta='2026-10-25')[1]['chambers'][0]['pending_recommendations'], 2)

    def test_singleton_and_timezone_inclusive(self):
        status, body = self.request(desde='2026-10-24T09:00:00-03:00', hasta='2026-10-24T12:00:00Z')
        self.assertEqual(status, 200)
        row = body['chambers'][0]
        self.assertEqual(row['consumption_total_kw'], 1)
        self.assertEqual(row['temperature']['desviacion_estandar'], 0)
        self.assertEqual(row['alerts'], 1)
        self.assertEqual(row['pending_recommendations'], 0)

    def test_empty_and_null_variable(self):
        status, body = self.request(desde='2026-10-26', hasta='2026-10-26', top=3)
        self.assertEqual(status, 200)
        self.assertEqual(len(body['chambers']), 10)
        for row in body['chambers']:
            self.assertEqual(row['temperature']['n'], 0)
            self.assertIsNone(row['consumption_total_kw'])
            self.assertEqual(row['alerts'], 0)
            self.assertEqual(row['pending_recommendations'], 0)
        self.assertEqual(body['rankings']['top_consumption'], [])
        self.assertEqual([r['id_chamber'] for r in body['rankings']['top_alerts']],
                         [str(c) for c in self.ids[:3]])
        self.db.query(Chamber).update({Chamber.active: False})
        self.db.commit()
        self.assertEqual(self.request()[1]['chambers'], [])

    def test_ties_and_null_consumption(self):
        self.db.query(SensorData).filter(SensorData.id_chamber.in_(self.ids[:2])).update(
            {SensorData.consumption_kw: 50}, synchronize_session=False)
        self.db.query(SensorData).filter(SensorData.id_chamber == self.ids[2]).update(
            {SensorData.consumption_kw: None})
        self.db.commit()
        body = self.request(top=2)[1]
        self.assertEqual([r['id_chamber'] for r in body['rankings']['top_consumption']],
                         [str(c) for c in self.ids[:2]])
        self.assertEqual(body['chambers'][2]['temperature']['n'], 2)
        self.assertIsNone(body['chambers'][2]['consumption_total_kw'])

    def test_invalid_filters(self):
        for changes in [dict(desde=None), dict(hasta=None), dict(desde='bad'),
                        dict(hasta='2026-02-30'), dict(desde='2026-10-25'),
                        dict(top=0), dict(top=101), dict(top='bad')]:
            with self.subTest(changes=changes):
                self.assertEqual(self.request(**changes)[0], 422)


if __name__ == '__main__':
    unittest.main()
