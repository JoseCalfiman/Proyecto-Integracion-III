# main.py
import threading
import logging
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "worker-predictivo"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    server = ThreadingHTTPServer(("0.0.0.0", 8000), HealthHandler)
    logging.info("Servidor HTTP de salud iniciado en el puerto 8000")
    server.serve_forever()


# 1) Primero la salud, antes de importar nada pesado
threading.Thread(target=start_health_server, daemon=True).start()

# 2) Recién ahora los imports del proyecto
logging.info("Importando config...")
import config
logging.info("Importando db...")
import db
from db import crear_tablas
logging.info("Importando kafka_consumer...")
from kafka_consumer import PredictiveKafkaWorker
logging.info("Imports listos")

if __name__ == "__main__":
    logging.info("Iniciando microservicio worker-predictivo...")
    while True:
        try:
            crear_tablas()
            logging.info("Tablas de BD verificadas/creadas correctamente.")
            worker = PredictiveKafkaWorker()
            worker.start_listening()
        except Exception as e:
            logging.error(f"Error crítico en el proceso principal: {e}. Reintentando en 10s...")
            time.sleep(10)