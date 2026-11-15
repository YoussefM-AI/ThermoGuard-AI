/*
 ============================================================================
  ThermoGuard AI - Wokwi Online ESP32 & DHT22 Simulation Firmware
 ============================================================================
  Circuit Configuration:
    - Microcontroller: ESP32 DevKit V1
    - Virtual Sensor: DHT22 connected to GPIO 4
    - Wi-Fi Network: Wokwi-GUEST (built-in Wokwi virtual Wi-Fi)

  How to Connect to your ThermoGuard AI Dashboard:
    - If using Wokwi IoT Gateway:
        Use: "http://10.0.2.2:5000/api/readings"
    - If using Cloud Hosting (Render / Railway / etc.):
        Use: "https://<your-app-domain>/api/readings"
    - If using Tunnel (Cloudflared / Ngrok / Localtunnel):
        Use: "https://<your-tunnel-url>/api/readings"
 ============================================================================
*/

#include "DHT.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>

// Hardware Pin Configuration
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// Virtual Wi-Fi
const char* SSID = "Wokwi-GUEST";
const char* PASS = "";

// --------------------------------------------------------------------------
// DASHBOARD ENDPOINT CONFIGURATION
// Update this URL with your active dashboard endpoint:
// --------------------------------------------------------------------------
const char* DASHBOARD_URL = "http://10.0.2.2:5000/api/readings";

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n========================================================");
  Serial.println("  ThermoGuard AI - Virtual ESP32 Node Initializing...   ");
  Serial.println("========================================================");
  
  dht.begin();
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID, PASS);
  
  Serial.printf("[WIFI] Connecting to %s", SSID);
  for (int i = 0; i < 30 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected! Assigned IP: " + WiFi.localIP().toString());
    Serial.printf("[TARGET] Streaming telemetry to: %s\n", DASHBOARD_URL);
  } else {
    Serial.println("\n[WIFI] Initial connection timed out - will retry in loop.");
  }
}

void loop() {
  delay(3000); // Read every 3 seconds
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WIFI] Reconnecting to Wokwi-GUEST...");
    WiFi.begin(SSID, PASS);
    return;
  }

  // Read virtual DHT22 on GPIO 4
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (isnan(t) || isnan(h)) {
    Serial.println("[SENSOR ERROR] Failed to read from virtual DHT22 on GPIO 4!");
    return;
  }

  Serial.printf("\n[DHT22] Reading: Temp = %.1f C | Hum = %.1f %%\n", t, h);

  // Dispatch HTTP POST to ThermoGuard AI Dashboard
  HTTPClient http;
  String targetUrl = String(DASHBOARD_URL);
  bool isHttps = targetUrl.startsWith("https://");

  bool beginSuccess = false;
  WiFiClient standardClient;
  WiFiClientSecure secureClient;

  if (isHttps) {
    secureClient.setInsecure(); // Accept all certificates for simulation/dev tunnels
    beginSuccess = http.begin(secureClient, targetUrl);
  } else {
    beginSuccess = http.begin(standardClient, targetUrl);
  }

  if (!beginSuccess) {
    Serial.println("    [HTTP ERROR] Unable to parse or connect to target URL.");
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.setTimeout(4000);

  // JSON payload tagged as source="HARDWARE"
  char payload[128];
  snprintf(payload, sizeof(payload), "{\"temperature\":%.2f,\"humidity\":%.2f,\"source\":\"HARDWARE\"}", t, h);

  int httpCode = http.POST((uint8_t*)payload, strlen(payload));

  if (httpCode == 200 || httpCode == 201) {
    Serial.printf("    [SUCCESS %d] Telemetry delivered to ThermoGuard AI Dashboard!\n", httpCode);
  } else if (httpCode > 0) {
    Serial.printf("    [SERVER RESPONSE %d] Server replied: %s\n", httpCode, http.getString().c_str());
  } else {
    Serial.printf("    [NETWORK ERROR %d] %s\n", httpCode, http.errorToString(httpCode).c_str());
    Serial.println("    -> Ensure backend is running and DASHBOARD_URL is reachable.");
  }

  http.end();
}
