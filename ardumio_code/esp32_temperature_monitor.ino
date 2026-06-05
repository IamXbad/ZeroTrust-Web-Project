#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"

// -------- PIN CONFIG --------
#define DHTPIN 4
#define DHTTYPE DHT11
#define TRIGGER_PIN 5

DHT dht(DHTPIN, DHTTYPE);

// -------- WIFI CONFIG --------
const char* ssid = "Biswa";
const char* password = "12345678";

// -------- SERVER --------
const char* serverName = "http://10.78.77.238:5001/edge_data";

// -------- BUTTON STATE --------
bool lastState = HIGH;

// -------- SETUP --------
void setup() {
  Serial.begin(115200);

  dht.begin();
  pinMode(TRIGGER_PIN, INPUT_PULLUP);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
}

// -------- FUNCTION: SEND DATA --------
void sendData() {

  Serial.println("Trigger detected! Sending data...");

  float temperature = dht.readTemperature();

  if (isnan(temperature)) {
    Serial.println("❌ Failed to read from DHT!");
    return;
  }

  Serial.print("Temperature: ");
  Serial.println(temperature);

  HTTPClient http;
  http.begin(serverName);
  http.addHeader("Content-Type", "application/json");

  String jsonData = "{\"device_id\":\"esp32_01\",\"temperature\":";
  jsonData += temperature;
  jsonData += "}";

  int httpResponseCode = http.POST(jsonData);

  Serial.print("HTTP Response code: ");
  Serial.println(httpResponseCode);

  http.end();
}

// -------- LOOP --------
void loop() {

  bool currentState = digitalRead(TRIGGER_PIN);

  // Detect button press (edge detection)
  if (lastState == HIGH && currentState == LOW) {
    sendData();
    delay(150);  // small debounce (optional)
  }

  lastState = currentState;
}