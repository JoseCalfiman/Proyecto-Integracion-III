"""Confirmación de entrega y propagación de errores sin un broker externo."""

import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch


with patch("confluent_kafka.Producer"), patch("dotenv.load_dotenv"):
    spec = importlib.util.spec_from_file_location(
        "ingesta_kafka_test", Path(__file__).resolve().parents[1] / "kafka_producer.py",
    )
    kafka = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kafka)


class KafkaDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "id_chamber": "44444444-4444-4444-4444-444444444444",
            "timestamp": "2026-10-15T18:45:30Z", "temperature": 4.7, "consumption_kw": 1.82,
        }
        self.message = MagicMock()
        self.message.topic.return_value = "sensor.raw"
        self.message.partition.return_value = 2
        self.message.key.return_value = self.payload["id_chamber"].encode()
        self.message.offset.return_value = 42

    def fake_flush(self, producer, error=None, pending=0):
        def complete(timeout):
            producer.produce.call_args.kwargs["callback"](error, self.message)
            return pending
        producer.flush.side_effect = complete

    def test_success_waits_for_callback_and_logs_broker_metadata(self):
        with patch.object(kafka, "producer") as producer, patch("builtins.print") as log:
            self.fake_flush(producer)
            kafka.publish_sensor_data(self.payload)
            producer.produce.assert_called_once()
            args, kwargs = producer.produce.call_args
            self.assertEqual(args, ("sensor.raw",))
            self.assertEqual(kwargs["key"], self.payload["id_chamber"])
            self.assertEqual(json.loads(kwargs["value"]), self.payload)
            producer.flush.assert_called_once_with(kafka.FLUSH_TIMEOUT_SECONDS)
            message = log.call_args.args[0]
            for text in ("confirmada", "topic=sensor.raw", "partition=2",
                         f"key={self.payload['id_chamber']}", "offset=42"):
                self.assertIn(text, message)

    def test_delivery_failure_is_raised_even_when_flush_has_no_pending_messages(self):
        with patch.object(kafka, "producer") as producer:
            self.fake_flush(producer, error="Message timed out")
            with self.assertRaisesRegex(kafka.KafkaPublishError, "partition=2.*Message timed out"):
                kafka.publish_sensor_data(self.payload)

    def test_pending_messages_are_not_success(self):
        with patch.object(kafka, "producer") as producer:
            producer.flush.return_value = 1
            with self.assertRaisesRegex(kafka.KafkaPublishError, "sin confirmar.*pendientes=1"):
                kafka.publish_sensor_data(self.payload)

    def test_empty_queue_without_callback_is_not_confirmation(self):
        with patch.object(kafka, "producer") as producer:
            producer.flush.return_value = 0
            with self.assertRaisesRegex(kafka.KafkaPublishError, "sin confirmar"):
                kafka.publish_sensor_data(self.payload)

    def test_enqueue_and_flush_exceptions_include_key_and_topic(self):
        for operation in ("produce", "flush"):
            with self.subTest(operation=operation), patch.object(kafka, "producer") as producer:
                getattr(producer, operation).side_effect = BufferError("queue failure")
                with self.assertRaisesRegex(kafka.KafkaPublishError, "topic=sensor.raw.*key=.*queue failure"):
                    kafka.publish_sensor_data(self.payload)

    def test_missing_key_is_rejected_before_enqueue(self):
        with patch.object(kafka, "producer") as producer:
            with self.assertRaisesRegex(kafka.KafkaPublishError, "falta id_chamber"):
                kafka.publish_sensor_data({"temperature": 4.7})
            producer.produce.assert_not_called()

    def test_shutdown_flush_is_bounded_and_reports_pending(self):
        with patch.object(kafka, "producer") as producer:
            producer.flush.return_value = 1
            with self.assertRaisesRegex(kafka.KafkaPublishError, "Cierre Kafka incompleto"):
                kafka.flush()
            producer.flush.assert_called_once_with(kafka.FLUSH_TIMEOUT_SECONDS)

    def test_shutdown_flush_completes_with_empty_queue(self):
        with patch.object(kafka, "producer") as producer:
            producer.flush.return_value = 0
            kafka.flush()


if __name__ == "__main__":
    unittest.main()
