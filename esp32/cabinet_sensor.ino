/*
 ============================================================================
  ThermoGuard AI - ESP32 & DHT11 Industrial Cabinet Telemetry Firmware
 ============================================================================
  Hardware Requirements:
    - ESP32 Development Board (e.g. ESP32-WROOM-32)
    - DHT11 Temperature & Humidity Sensor (3-pin module or 4-pin bare)
    - 10k Ohm pull-up resistor (only if using 4-pin bare sensor)
    - Breadboard and jumper wires
    - USB Data Cable

  Wiring Diagram:
    +-----------------+-----------------------+
    | DHT11 Pin       | ESP32 Pin             |
    +-----------------+-----------------------+
    | VCC (+)         | 3V3 (3.3V Power Out)  |
    | DATA (OUT)      | GPIO 4 (Digital I/O)  |
    | GND (-)         | GND (Ground)          |
    +-----------------+-----------------------+

  Note: If using a 3-pin DHT11 module with a small PCB, the pull-up resistor
  is already onboard. If using a bare 4-pin DHT11, place a 10k resistor
  between VCC (3.3V) and DATA (GPIO 4), and leave pin 3 unconnected.
 ============================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>
#include "DHT.h"

// -------------------------------------------------------------
// USER CONFIGURATION (Update with your local network settings)
// -------------------------------------------------------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";         // Enter your Wi-Fi SSID
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";     // Enter your Wi-Fi Password

// -------------------------------------------------------------
// HYBRID IOT CLOUD / LOCAL CONFIGURATION
// -------------------------------------------------------------
// Set to true to transmit directly to cloud (PC can be turned off)
// Set to false to transmit to your local machine on LAN
const bool  USE_CLOUD_ENDPOINT = false;

// Mode A: Local PC / LAN Development (when backend runs on your machine)
const char* LOCAL_SERVER_IP    = "192.168.1.100";     // e.g. "192.168.1.50"
const int   LOCAL_SERVER_PORT  = 5000;

// Mode B: Standalone Cloud AI Hosting (Render, Railway, Fly.io, etc.)
const char* CLOUD_SERVER_URL   = "https://your-thermoguard-ai.onrender.com/api/readings";

// Hardware Pin Configuration
#define DHTPIN  4                                     // Digital GPIO pin connected to DHT11 DATA
#define DHTTYPE DHT11                                 // Physical sensor model: DHT11

// Sampling Cadence: Read temperature and humidity every 3 seconds
const unsigned long SAMPLING_INTERVAL_MS = 3000;

// -------------------------------------------------------------
// GLOBAL INSTANCES & STATE
// -------------------------------------------------------------
DHT dht(DHTPIN, DHTTYPE);
unsigned long lastReadTime = 0;
int consecutiveErrors = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n========================================================");
  Serial.println("  ThermoGuard AI - ESP32 Industrial Node Starting...    ");
  Serial.println("========================================================");
  
  // Initialize DHT11 sensor
  Serial.printf("[SENSOR] Initializing DHT11 on GPIO %d...\n", DHTPIN);
  dht.begin();
  
  // Connect to Wi-Fi
  connectWiFi();
}

void loop() {
  // Ensure Wi-Fi link remains active
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WIFI] Warning: Connection lost. Reconnecting...");
    connectWiFi();
  }

  // Periodic Telemetry Acquisition
  unsigned long currentMillis = millis();
  if (currentMillis - lastReadTime >= SAMPLING_INTERVAL_MS) {
    lastReadTime = currentMillis;
    readAndTransmitTelemetry();
  }
}

// -------------------------------------------------------------
// WI-FI CONNECTION HELPER
// -------------------------------------------------------------
void connectWiFi() {
  Serial.printf("[WIFI] Connecting to SSID: %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected successfully!");
    Serial.printf("[WIFI] IP Address: %s | RSSI: %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
    if (USE_CLOUD_ENDPOINT) {
      Serial.printf("[MODE] Cloud AI Mode -> Target: %s\n", CLOUD_SERVER_URL);
    } else {
      Serial.printf("[MODE] Local Mode -> Target: http://%s:%d/api/readings\n", LOCAL_SERVER_IP, LOCAL_SERVER_PORT);
    }
  } else {
    Serial.println("\n[WIFI] Connection failed. Will retry on next sampling cycle.");
  }
}

// -------------------------------------------------------------
// SENSOR READING & HTTP REST TRANSMISSION
// -------------------------------------------------------------
void readAndTransmitTelemetry() {
  // Reading temperature & humidity from DHT11
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature(); // Celsius

  // Validate sensor output
  if (isnan(humidity) || isnan(temperature)) {
    consecutiveErrors++;
    Serial.printf("[SENSOR ERROR] Failed to read from DHT11 sensor! (Consecutive failures: %d)\n", consecutiveErrors);
    Serial.println("               Check wiring: VCC -> 3V3, GND -> GND, DATA -> GPIO 4.");
    return;
  }

  // Physical bounds sanity check (DHT11 rated: 0-50°C, 20-90% RH)
  if (temperature < -10.0 || temperature > 80.0 || humidity < 5.0 || humidity > 100.0) {
    Serial.printf("[SENSOR WARNING] Reading out of physical sanity range: Temp=%.1fC, Hum=%.1f%%\n", temperature, humidity);
  }

  consecutiveErrors = 0;
  Serial.printf("\n[DHT11] Measured: Temp = %.1f °C | Humidity = %.1f %%\n", temperature, humidity);

  // Skip HTTP transmission if Wi-Fi is not connected
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] Wi-Fi offline. Telemetry transmission skipped.");
    return;
  }

  HTTPClient http;
  bool beginSuccess = false;
  WiFiClient standardClient;
  WiFiClientSecure secureClient;

  if (USE_CLOUD_ENDPOINT) {
    secureClient.setInsecure(); // Accept SSL certs for cloud instance
    beginSuccess = http.begin(secureClient, CLOUD_SERVER_URL);
  } else {
    char serverEndpoint[128];
    snprintf(serverEndpoint, sizeof(serverEndpoint), "http://%s:%d/api/readings", LOCAL_SERVER_IP, LOCAL_SERVER_PORT);
    beginSuccess = http.begin(standardClient, serverEndpoint);
  }

  if (!beginSuccess) {
    Serial.println("[HTTP ERROR] Failed to initialize connection to server endpoint.");
    return;
  }

  // Construct JSON Payload (Tagged source="HARDWARE")
  char jsonPayload[128];
  snprintf(jsonPayload, sizeof(jsonPayload),
    "{\"temperature\":%.2f,\"humidity\":%.2f,\"source\":\"HARDWARE\"}",
    temperature, humidity
  );

  http.addHeader("Content-Type", "application/json");
  http.setTimeout(4000); // 4 second timeout

  int httpResponseCode = http.POST((uint8_t*)jsonPayload, strlen(jsonPayload));

  if (httpResponseCode == 200 || httpResponseCode == 201) {
    String responseBody = http.getString();
    Serial.printf("[HTTP SUCCESS %d] Telemetry delivered to ThermoGuard AI -> Response: %s\n", httpResponseCode, responseBody.c_str());
  } else if (httpResponseCode > 0) {
    Serial.printf("[HTTP POST %d] Server replied: %s\n", httpResponseCode, http.getString().c_str());
  } else {
    Serial.printf("[HTTP ERROR] POST failed, error code: %d (%s)\n", httpResponseCode, http.errorToString(httpResponseCode).c_str());
  }

  http.end();
}
