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
from models import SensorData
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
        path = '/api/v1/stats/chambers/' + chamber
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


if __name__ == '__main__':
    unittest.main()
