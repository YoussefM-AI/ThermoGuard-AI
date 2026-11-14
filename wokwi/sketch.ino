/*
 ============================================================================
  CabinetSense AI - Wokwi Online ESP32 & DHT Simulation Firmware
 ============================================================================
  Simulator: https://wokwi.com/
  Hardware in Simulation:
    - ESP32 DevKit V1
    - DHT22 / DHT11 Sensor (connected to GPIO 4)
    - Virtual Wi-Fi: "Wokwi-GUEST" (Free public Wokwi simulated network)

  How to test anomalies in Wokwi:
    1. Click the "Play" button in Wokwi.
    2. Click on the DHT sensor component during simulation.
    3. Use the popup sliders to change Temperature and Humidity live!
 ============================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"

// -------------------------------------------------------------
// WOKWI SIMULATION WI-FI CONFIGURATION
// -------------------------------------------------------------
const char* WIFI_SSID     = "Wokwi-GUEST";  // Default Wokwi Virtual Wi-Fi
const char* WIFI_PASSWORD = "";             // No password required in Wokwi

// -------------------------------------------------------------
// FLASK BACKEND CONFIGURATION
// -------------------------------------------------------------
// Option 1: If using Wokwi IoT Gateway locally -> "http://10.0.2.2:5000/api/readings"
// Option 2: If using ngrok/localtunnel -> "https://YOUR_TUNNEL_URL/api/readings"
// Option 3: Local LAN IP (if Wokwi Gateway is running) -> "http://192.168.1.X:5000/api/readings"
const char* SERVER_ENDPOINT = "http://10.0.2.2:5000/api/readings";

// Hardware Pin Configuration
#define DHTPIN  4                                     // Digital GPIO pin connected to DHT DATA
#define DHTTYPE DHT22                                 // Wokwi uses DHT22 / DHT11 model

// Sampling Cadence (every 2.5 seconds)
const unsigned long SAMPLING_INTERVAL_MS = 2500;

DHT dht(DHTPIN, DHTTYPE);
unsigned long lastReadTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================================");
  Serial.println("  CabinetSense AI - WOKWI ESP32 Simulator Starting...   ");
  Serial.println("========================================================");

  // Initialize DHT sensor
  Serial.printf("[SENSOR] Initializing DHT on GPIO %d...\n", DHTPIN);
  dht.begin();

  // Connect to Wokwi Virtual Wi-Fi
  connectWokwiWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWokwiWiFi();
  }

  unsigned long currentMillis = millis();
  if (currentMillis - lastReadTime >= SAMPLING_INTERVAL_MS) {
    lastReadTime = currentMillis;
    readAndSendTelemetry();
  }
}

void connectWokwiWiFi() {
  Serial.print("[WIFI] Connecting to Wokwi-GUEST...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected to Wokwi Virtual Wi-Fi!");
    Serial.printf("[WIFI] Simulated IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WIFI] Connection retry pending...");
  }
}

void readAndSendTelemetry() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("[SENSOR ERROR] Failed to read from simulated DHT sensor.");
    return;
  }

  Serial.println("--------------------------------------------------------");
  Serial.printf("[WOKWI SENSOR] Temp: %.2f °C | Humidity: %.2f %%\n", temperature, humidity);

  // Construct JSON Payload (Tagged source="HARDWARE" so dashboard recognizes it as real device)
  char jsonPayload[128];
  snprintf(jsonPayload, sizeof(jsonPayload),
    "{\"temperature\":%.2f,\"humidity\":%.2f,\"source\":\"HARDWARE\"}",
    temperature, humidity
  );

  // Send HTTP POST to Flask Backend
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_ENDPOINT);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(3000);

    Serial.printf("[HTTP POST] Sending payload to: %s\n", SERVER_ENDPOINT);
    Serial.printf("            Payload: %s\n", jsonPayload);

    int httpCode = http.POST((uint8_t*)jsonPayload, strlen(jsonPayload));

    if (httpCode > 0) {
      String response = http.getString();
      Serial.printf("[HTTP SUCCESS] Code: %d -> Server Response: %s\n", httpCode, response.c_str());
    } else {
      Serial.printf("[HTTP NOTE] POST attempt (code %d: %s)\n", httpCode, http.errorToString(httpCode).c_str());
      Serial.println("            Tip: To route Wokwi to localhost:5000, use ngrok or Wokwi IoT Gateway.");
    }
    http.end();
  }
}
