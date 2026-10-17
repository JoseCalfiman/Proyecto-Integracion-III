"""Pruebas del callback MQTT sin conexiones a PostgreSQL, Kafka ni MQTT."""

import importlib.util
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID


INGESTA = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


schemas = load_module("schemas", INGESTA / "schemas.py")
with patch.dict(sys.modules, {
    "database": MagicMock(),
    "kafka_producer": MagicMock(),
    "models": MagicMock(),
    "schemas": schemas,
}), patch("dotenv.load_dotenv"), patch("paho.mqtt.client.Client"):
    mqtt_client = load_module("ingesta_mqtt_test", INGESTA / "mqtt_client.py")


class MqttPayloadTests(unittest.TestCase):
    def setUp(self):
        # Payload real de Wokwi proporcionado por el responsable de Ingesta.
        self.payload = {
            "id_chamber": "44444444-4444-4444-4444-444444444444",
            "temperature": 4.7,
            "consumption_kw": 1.82,
            "timestamp": "2026-10-15T18:45:30Z",
        }

    def test_mqtt_aliases_persist_and_publish_canonical_fields(self):
        for chamber_field in ("id_chamber", "chamber_id"):
            for time_field in ("timestamp", "recorded_at"):
                with self.subTest(chamber_field=chamber_field, time_field=time_field):
                    payload = {
                        chamber_field: self.payload["id_chamber"],
                        time_field: self.payload["timestamp"],
                        "temperature": self.payload["temperature"],
                        "consumption_kw": self.payload["consumption_kw"],
                    }
                    raw = json.dumps(payload)
                    with patch.object(mqtt_client, "SessionLocal") as session, \
                         patch.object(mqtt_client, "SensorData") as model, \
                         patch.object(mqtt_client, "log_ingestion") as log, \
                         patch.object(mqtt_client, "publish_sensor_data") as publish:
                        mqtt_client.on_message(None, None, SimpleNamespace(
                            payload=raw.encode(), topic="sensor/raw",
                        ))
                        reading = schemas.SensorDataCreate(**payload)
                        model.assert_called_once_with(
                            id_chamber=reading.id_chamber,
                            timestamp=datetime(2026, 10, 15, 18, 45, 30, tzinfo=timezone.utc),
                            temperature=4.7,
                            consumption_kw=1.82,
                        )
                        session.return_value.add.assert_called_once_with(model.return_value)
                        session.return_value.commit.assert_called_once()
                        session.return_value.close.assert_called_once()
                        published = publish.call_args.args[0]
                        self.assertEqual(published["id_chamber"], self.payload["id_chamber"])
                        self.assertEqual(schemas.SensorDataCreate(**published), reading)
                        self.assertEqual(published["temperature"], 4.7)
                        self.assertEqual(published["consumption_kw"], 1.82)
                        self.assertNotIn("chamber_id", published)
                        self.assertNotIn("recorded_at", published)
                        json.dumps(published)  # UUID y datetime deben ser serializables.
                        self.assertEqual([c.args[1] for c in log.call_args_list], ["success"])
                        self.assertNotIn("error_message", log.call_args.kwargs)
                        for call in log.call_args_list:
                            self.assertEqual(call.kwargs["id_chamber"], UUID(self.payload["id_chamber"]))

    def test_invalid_fields_do_not_persist_or_publish(self):
        for field, value in (("id_chamber", "invalid"), ("timestamp", "invalid"),
                             ("timestamp", "2026-10-15T18:45:30"),
                             ("timestamp", "2026-10-15"), ("timestamp", 1792089930),
                             ("temperature", 100), ("temperature", -51),
                             ("temperature", True), ("temperature", "4.7"),
                             ("temperature", float("nan")), ("temperature", float("inf")),
                             ("consumption_kw", -1), ("consumption_kw", 1000),
                             ("consumption_kw", False), ("consumption_kw", "1.82"),
                             ("consumption_kw", float("nan")), ("consumption_kw", float("inf")),
                             ("timestamp", None), ("temperature", None), ("consumption_kw", None)):
            with self.subTest(field=field), \
                 patch.object(mqtt_client, "SessionLocal") as session, \
                 patch.object(mqtt_client, "log_ingestion") as log, \
                 patch.object(mqtt_client, "publish_sensor_data") as publish:
                payload = {**self.payload, field: value}
                mqtt_client.procesar_payload(payload, json.dumps(payload))
                session.assert_not_called()
                publish.assert_not_called()
                log.assert_called_once()
                self.assertEqual(log.call_args.args[1], "error")
                self.assertIn(field, log.call_args.kwargs["error_message"])

    def test_missing_fields_and_non_objects_are_rejected(self):
        payloads = [None, [], "reading", 42]
        for field in ("temperature", "consumption_kw", "timestamp", "id_chamber"):
            payloads.append({k: v for k, v in self.payload.items() if k != field})
        for payload in payloads:
            with self.subTest(payload=payload), \
                 patch.object(mqtt_client, "SessionLocal") as session, \
                 patch.object(mqtt_client, "log_ingestion") as log, \
                 patch.object(mqtt_client, "publish_sensor_data") as publish:
                raw = json.dumps(payload)
                mqtt_client.on_message(None, None, SimpleNamespace(payload=raw.encode(), topic="sensor/raw"))
                session.assert_not_called()
                publish.assert_not_called()
                log.assert_called_once()
                self.assertEqual(log.call_args.args[1], "error")
                self.assertTrue(log.call_args.kwargs["error_message"])

    def test_numeric_boundaries_are_valid(self):
        for temperature, consumption in ((-50, 0), (50, 999.999)):
            reading = schemas.SensorDataCreate(**{
                **self.payload, "temperature": temperature, "consumption_kw": consumption,
            })
            self.assertEqual(reading.temperature, temperature)
            self.assertEqual(reading.consumption_kw, consumption)

    def test_invalid_json_is_logged_without_saving(self):
        with patch.object(mqtt_client, "SessionLocal") as session, \
             patch.object(mqtt_client, "log_ingestion") as log:
            mqtt_client.on_message(None, None, SimpleNamespace(payload=b'{broken', topic="sensor/raw"))
            session.assert_not_called()
            log.assert_called_once()
            self.assertEqual(log.call_args.args[:2], ("{broken", "error"))
            self.assertIn("JSON invalido", log.call_args.kwargs["error_message"])

    def test_database_failure_rolls_back_and_logs_error(self):
        with patch.object(mqtt_client, "SessionLocal") as session, \
             patch.object(mqtt_client, "log_ingestion") as log, \
             patch.object(mqtt_client, "publish_sensor_data") as publish:
            session.return_value.commit.side_effect = RuntimeError("No existe la cámara")
            mqtt_client.procesar_payload(self.payload, json.dumps(self.payload))
            session.return_value.rollback.assert_called_once()
            session.return_value.close.assert_called_once()
            publish.assert_not_called()
            log.assert_called_once()
            self.assertEqual(log.call_args.args[1], "error")
            self.assertEqual(log.call_args.kwargs["error_message"], "No existe la cámara")

    def test_publication_exception_logs_error_after_valid_reading_is_saved(self):
        with patch.object(mqtt_client, "SessionLocal") as session, \
             patch.object(mqtt_client, "log_ingestion") as log, \
             patch.object(mqtt_client, "publish_sensor_data", side_effect=RuntimeError("Cola Kafka llena")):
            mqtt_client.procesar_payload(self.payload, json.dumps(self.payload))
            session.return_value.commit.assert_called_once()
            log.assert_called_once()
            self.assertEqual(log.call_args.args[1], "error")
            self.assertEqual(log.call_args.kwargs["error_message"], "Cola Kafka llena")

    def test_log_persists_final_status_and_error_even_for_unknown_chamber(self):
        for status, error in (("success", None), ("error", "temperatura inválida")):
            for exists in (True, False):
                with self.subTest(status=status, exists=exists), \
                     patch.object(mqtt_client, "SessionLocal") as session, \
                     patch.object(mqtt_client, "IngestionLog") as model:
                    chamber_id = UUID(self.payload["id_chamber"])
                    session.return_value.get.return_value = object() if exists else None
                    mqtt_client.log_ingestion("original", status, chamber_id, error)
                    model.assert_called_once_with(
                        id_chamber=chamber_id if exists else None,
                        received_payload="original", processing_status=status, error_message=error,
                    )
                    session.return_value.add.assert_called_once_with(model.return_value)
                    session.return_value.commit.assert_called_once()
                    session.return_value.close.assert_called_once()

    def test_extract_chamber_id_handles_missing_or_invalid_values(self):
        for payload in ({}, {"chamber_id": "invalid"}, None, []):
            self.assertIsNone(mqtt_client._extraer_chamber_id(payload))


class MqttConfigurationTests(unittest.TestCase):
    def test_ingesta_credentials_take_priority_and_legacy_pair_is_supported(self):
        cases = [
            ({"MQTT_INGESTA_USER": "ingesta", "MQTT_INGESTA_PASSWORD": "test-ingesta",
              "MQTT_USER": "legacy", "MQTT_PASSWORD": "test-legacy"},
             ("ingesta", "test-ingesta")),
            ({"MQTT_USER": "legacy", "MQTT_PASSWORD": "test-legacy"},
             ("legacy", "test-legacy")),
            ({"MQTT_INGESTA_USER": "ingesta", "MQTT_PASSWORD": "test-legacy"}, None),
            ({}, None),
        ]
        for credentials, expected in cases:
            with self.subTest(credentials=list(credentials)), \
                 patch.dict(os.environ, {"MQTT_BROKER_HOST": "mosquitto",
                                         "MQTT_BROKER_PORT": "1883", **credentials}, clear=True), \
                 patch.dict(sys.modules, {"database": MagicMock(), "models": MagicMock(),
                                          "kafka_producer": MagicMock(), "schemas": schemas}), \
                 patch("dotenv.load_dotenv"), patch("paho.mqtt.client.Client") as client:
                module = load_module("ingesta_mqtt_config_test", INGESTA / "mqtt_client.py")
                self.assertEqual(module.MQTT_BROKER, "mosquitto")
                self.assertEqual(module.MQTT_PORT, 1883)
                if expected:
                    client.return_value.username_pw_set.assert_called_once_with(*expected)
                else:
                    client.return_value.username_pw_set.assert_not_called()


if __name__ == "__main__":
    unittest.main()
