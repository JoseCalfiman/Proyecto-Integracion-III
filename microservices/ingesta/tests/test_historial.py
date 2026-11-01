"""Contrato HTTP de historial con una base SQLite aislada, sin servicios externos."""
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
from routes.historial import router


class HistorialTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        metadata = MetaData()
        for table in SensorData.metadata.tables.values():
            table.to_metadata(metadata)
        metadata.tables["sensor_data"].c.id_data.autoincrement = False
        metadata.tables["sensor_data"].create(self.engine)
        self.db = Session(self.engine)
        self.chamber = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        for identifier, chamber, timestamp, temperature, power in [
            (1, self.chamber, '2026-10-23T23:59:59', -20, 1),
            (2, self.chamber, '2026-10-24T00:00:00', -18, 1.25),
            (3, self.chamber, '2026-10-24T23:59:59', None, None),
            (4, UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), '2026-10-24T12:00:00', -10, 2),
            (5, self.chamber, '2026-10-25T00:00:00', -17, 3),
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
        messages = []

        async def run():
            async def receive():
                return {'type': 'http.request', 'body': b'', 'more_body': False}

            async def send(message):
                messages.append(message)

            await self.app({'type': 'http', 'asgi': {'version': '3.0'},
                            'http_version': '1.1', 'method': 'GET', 'scheme': 'http',
                            'path': '/api/v1/historial', 'raw_path': b'/api/v1/historial',
                            'query_string': urlencode(params).encode(), 'headers': [],
                            'server': ('test', 80), 'client': ('test', 1)}, receive, send)
        asyncio.run(run())
        return messages[0]['status'], json.loads(b''.join(m.get('body', b'') for m in messages[1:]))

    def test_date_range_chamber_order_and_nullable_numeric_contract(self):
        status, rows = self.request()
        self.assertEqual(status, 200)
        self.assertEqual([r['id_data'] for r in rows], [2, 3])
        self.assertEqual(rows[0]['temperature'], -18.0)
        self.assertEqual(rows[0]['consumption_kw'], 1.25)
        self.assertIsNone(rows[1]['temperature'])
        self.assertEqual(rows[0]['id_chamber'], str(self.chamber))
        self.assertIn('timestamp', rows[0])

    def test_limit_and_empty_result(self):
        self.assertEqual(len(self.request(limit=1)[1]), 1)
        self.assertEqual(self.request(id_chamber=str(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"))), (200, []))

    def test_timestamp_end_is_inclusive_and_offsets_are_normalized(self):
        status, rows = self.request(desde='2026-10-23T21:00:00-03:00', hasta='2026-10-24T00:00:00Z')
        self.assertEqual(status, 200)
        self.assertEqual([r['id_data'] for r in rows], [2])

    def test_invalid_filters(self):
        for changes in [dict(id_chamber='invalid'), dict(id_chamber=None),
                        dict(desde=None), dict(hasta='bad'), dict(limit=0),
                        dict(limit=10001), dict(limit='x'),
                        dict(desde='2026-10-25', hasta='2026-10-24')]:
            with self.subTest(changes=changes):
                self.assertEqual(self.request(**changes)[0], 422)


if __name__ == '__main__':
    unittest.main()
