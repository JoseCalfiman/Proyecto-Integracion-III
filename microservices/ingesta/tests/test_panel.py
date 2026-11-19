"""Contrato HTTP del panel con inventario aislado y permisos reales."""
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import test_roles
from models import Chamber, Sensor, SensorData, GeneratedAlert
from fastapi.responses import JSONResponse


class PanelTests(test_roles.RoleMatrix):
    def test_inventory_and_empty(self):
        token = self.tokens['tecnico']
        for path in ('gateways', 'sensores'):
            self.assertEqual(self.request('GET', '/panel/'+path, token), (200, []))
        chamber = uuid4()
        with self.sessions.begin() as db:
            db.add(Chamber(id_chamber=chamber, name='Real', active=False))
            db.add(Sensor(id_sensor=42, id_chamber=chamber, sensor_type='temperature', status='maintenance'))
            db.add(Sensor(id_sensor=43, id_chamber=chamber, status='active'))
            db.add(SensorData(id_data=1, id_chamber=chamber, id_sensor=42,
                              timestamp=datetime(2026, 11, 1), temperature=-10))
            # Una lectura de cámara sin sensor no se atribuye a todos los sensores.
            db.add(SensorData(id_data=2, id_chamber=chamber,
                              timestamp=datetime(2026, 11, 2), temperature=-9))
        status, rows = self.request('GET', '/panel/gateways', token)
        self.assertEqual(status, 200)
        self.assertEqual(rows[0]['id'], str(chamber))
        self.assertEqual(rows[0]['sensores'], 2)
        self.assertEqual(rows[0]['estado'], 'unknown')
        self.assertIsNone(rows[0]['ping_ms'])
        self.assertFalse(rows[0]['active'])
        status, rows = self.request('GET', '/panel/sensores', token)
        self.assertEqual(status, 200)
        self.assertEqual([r['id'] for r in rows], [42, 43])
        self.assertEqual(rows[0]['estado'], 'maintenance')
        self.assertIsNone(rows[0]['bateria'])
        self.assertTrue(rows[0]['ultima_lectura'].startswith('2026-11-01'))
        self.assertIsNone(rows[1]['ultima_lectura'])
        status, rows = self.request('GET', '/panel/alertas', token)
        self.assertEqual(status, 200)
        self.assertEqual(rows[0]['id'], 1)
        self.assertEqual(rows[0]['codigo'], 'high')
        with self.sessions.begin() as db:
            db.query(GeneratedAlert).delete()
        self.assertEqual(self.request('GET', '/panel/alertas', token), (200, []))

    def test_panel_permissions(self):
        for path in ('gateways', 'sensores', 'alertas', 'health'):
            self.assertEqual(self.request('GET', '/panel/'+path)[0], 401)
            self.assertEqual(self.request('GET', '/panel/'+path, self.tokens['gerente'])[0], 403)

    def test_health_reports_failures(self):
        for db_status, mqtt_connected, expected in [('ok', True, 'ok'), ('error', False, 'degraded')]:
            with patch('readiness.ready', return_value=JSONResponse(content={'checks':{'db':db_status,'kafka':'ok'}})), patch('mqtt_client.client.is_connected', return_value=mqtt_connected):
                status, body = self.request('GET', '/panel/health', self.tokens['tecnico'])
            self.assertEqual(status, 200)
            self.assertEqual(body['status'], expected)
            self.assertEqual(body['checks']['db'], db_status)
            self.assertEqual(body['checks']['mqtt'], 'ok' if mqtt_connected else 'error')
