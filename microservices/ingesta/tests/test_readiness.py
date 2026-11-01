"""Pruebas de probes sin depender de DB, Kafka ni MQTT externos."""

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch("confluent_kafka.Producer"), patch("dotenv.load_dotenv"):
    spec = importlib.util.spec_from_file_location(
        "ingesta_readiness_test", Path(__file__).resolve().parents[1] / "readiness.py",
    )
    readiness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(readiness)


class ReadinessTests(unittest.TestCase):
    def test_dependency_states_and_recovery(self):
        for db_ok, kafka_ok in ((True, True), (False, True), (True, False), (False, False)):
            with self.subTest(db=db_ok, kafka=kafka_ok), \
                    patch.object(readiness, "probe_engine") as engine, \
                    patch.object(readiness, "producer") as producer:
                if not db_ok:
                    engine.connect.side_effect = RuntimeError("private DB credentials")
                if kafka_ok:
                    producer.list_topics.return_value.brokers = {1: MagicMock()}
                else:
                    producer.list_topics.side_effect = RuntimeError("private Kafka details")
                response = readiness.ready()
                self.assertEqual(response.status_code, 200 if db_ok and kafka_ok else 503)
                self.assertEqual(json.loads(response.body)["checks"], {
                    "db": "ok" if db_ok else "error",
                    "kafka": "ok" if kafka_ok else "error",
                })
                self.assertNotIn(b"private", response.body)
                producer.list_topics.assert_called_once_with(timeout=2)
                if db_ok:
                    connection = engine.connect.return_value.__enter__.return_value
                    self.assertEqual(str(connection.execute.call_args.args[0]), "SELECT 1")
                    engine.connect.return_value.__exit__.assert_called_once()

    def test_empty_broker_metadata_is_not_ready(self):
        with patch.object(readiness, "probe_engine"), patch.object(readiness, "producer") as producer:
            producer.list_topics.return_value.brokers = {}
            self.assertEqual(readiness.ready().status_code, 503)


if __name__ == "__main__":
    unittest.main()
