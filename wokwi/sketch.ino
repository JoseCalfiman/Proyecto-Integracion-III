#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// CONFIGURACIÓN

const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

//BROKER PÚBLICO (sin ngrok, sin tarjeta)
const char* MQTT_BROKER = "test.mosquitto.org";
const int MQTT_PORT = 1883;
const char* MQTT_CLIENT = "esp32-wokwi-cryometric";

const char* TOPIC_SENSOR = "sensor/raw";

// Pines
#define DHTPIN 15
#define DHTTYPE DHT22
#define POT_PIN 34

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient mqtt(espClient);

unsigned long lastPublish = 0;
const long PUBLISH_INTERVAL = 10000;  // 10 segundos

// ============================================================
// IDs DE LAS 3 CÁMARAS (según el MER oficial)
// ============================================================
const char* CAMARAS[] = {
  "44444444-4444-4444-4444-444444444444",  // Cámara Principal 01
  "55555555-5555-5555-5555-555555555555",  // Cámara Principal 02
  "66666666-6666-6666-6666-666666666666"   // Túnel de Enfriamiento A
};
const int NUM_CAMARAS = 3;


// FUNCIONES
void connectWiFi() {
  Serial.print("Conectando a WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado. IP: " + WiFi.localIP().toString());
}

void connectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("Conectando a MQTT...");
    String clientId = MQTT_CLIENT + String(random(0xffff), HEX);
    if (mqtt.connect(clientId.c_str())) {
      Serial.println("conectado!");
    } else {
      Serial.print("falló, rc=");
      Serial.print(mqtt.state());
      Serial.println(" reintentando en 5s...");
      delay(5000);
    }
  }
}

// SETUP
void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(POT_PIN, INPUT);

  connectWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  connectMQTT();
}

// LOOP

void loop() {
  if (!mqtt.connected()) connectMQTT();
  mqtt.loop();

  unsigned long now = millis();
  if (now - lastPublish >= PUBLISH_INTERVAL) {
    lastPublish = now;

    // Leer sensores base
    float tempBase = dht.readTemperature();
    if (isnan(tempBase)) {
      Serial.println("Error leyendo DHT22");
      return;
    }

    int potValue = analogRead(POT_PIN);
    float consumoBase = (potValue / 4095.0) * 3.5;

    // Publicar datos de cada cámara
    for (int i = 0; i < NUM_CAMARAS; i++) {
      float temp = tempBase + (i * 0.5) + (random(-50, 50) / 100.0);
      float consumo = consumoBase + (i * 0.3) + (random(-20, 20) / 100.0);

      String payload = "{";
      payload += "\"id_chamber\":\"" + String(CAMARAS[i]) + "\",";
      payload += "\"temperature\":" + String(temp, 2) + ",";
      payload += "\"consumption_kw\":" + String(consumo, 2) + ",";
      payload += "\"timestamp\":\"" + String(millis()) + "\"";
      payload += "}";

      Serial.print("Publicando cámara " + String(i + 1) + ": ");
      Serial.println(payload);
      mqtt.publish(TOPIC_SENSOR, payload.c_str());

      delay(100);
    }

    Serial.println("---");
  }
}

