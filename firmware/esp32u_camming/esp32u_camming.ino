#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoOTA.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>
#include "esp_wifi.h"

// Wi-Fi (two slots for redundancy)
const char *WIFI1_SSID = "trannyfix";
const char *WIFI1_PASS = "transgender";
const char *WIFI2_SSID = "HotMess";
const char *WIFI2_PASS = "transgender";

// MQTT
const char *MQTT_HOST = "10.42.0.1";
constexpr uint16_t MQTT_PORT = 1883;
const char *MQTT_USER = "";
const char *MQTT_PASS = "";
const char *MQTT_CMD_TOPIC = "esp32u/command";
const char *MQTT_STATUS_TOPIC = "esp32u/status";
// Lock to the Pi 2.4 GHz AP (trannyfix) to avoid hopping to other routers.
constexpr uint8_t AP_BSSID[6] = {0x98, 0x48, 0x27, 0xA2, 0x46, 0xD6};
constexpr int AP_CHANNEL = 11;

// LED layout: two strips of 300.
// NOTE: GPIO35 is input-only on ESP32; use GPIO32 instead for the second strip.
constexpr uint8_t STRIP_COUNT = 2;
constexpr uint8_t STRIP_PINS[STRIP_COUNT] = {33, 32};
constexpr uint16_t STRIP_LENGTHS[STRIP_COUNT] = {300, 300};
constexpr uint16_t MATRIX_WIDTH = 23;
constexpr uint16_t MATRIX_HEIGHT = 13;
constexpr uint16_t MATRIX_LENGTH = MATRIX_WIDTH * MATRIX_HEIGHT;  // 299
constexpr neoPixelType LED_TYPE = NEO_GRB + NEO_KHZ800;

Adafruit_NeoPixel strips[STRIP_COUNT] = {
    Adafruit_NeoPixel(STRIP_LENGTHS[0], STRIP_PINS[0], LED_TYPE),
    Adafruit_NeoPixel(STRIP_LENGTHS[1], STRIP_PINS[1], LED_TYPE),
};

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

struct State {
  String pattern = "white";
  float brightness = 200.0f;     // 0-255
  float whiteBalance = 4500.0f;  // Kelvin
  uint8_t color[3] = {255, 217, 187};
  bool hasColor = false;
  unsigned long lastUpdate = 0;
  float rainbowPhase = 0.0f;
} state;

// Forward declarations
void applyPatternNow();
void renderRainbow(float dt);
void renderRainbowHills(float dt);
const char *wifiStatusText(wl_status_t st) {
  switch (st) {
    case WL_IDLE_STATUS: return "idle";
    case WL_NO_SSID_AVAIL: return "no ssid";
    case WL_SCAN_COMPLETED: return "scan complete";
    case WL_CONNECTED: return "connected";
    case WL_CONNECT_FAILED: return "connect failed";
    case WL_CONNECTION_LOST: return "connection lost";
    case WL_DISCONNECTED: return "disconnected";
    default: return "unknown";
  }
}

uint32_t colorTempToRGB(float kelvin) {
  float k = constrain(kelvin, 1500.0f, 9000.0f) / 100.0f;
  float r, g, b;
  if (k <= 66) {
    r = 255;
    g = 99.4708025861 * log(k) - 161.1195681661;
    b = k <= 19 ? 0 : 138.5177312231 * log(k - 10) - 305.0447927307;
  } else {
    r = 329.698727446 * pow(k - 60, -0.1332047592);
    g = 288.1221695283 * pow(k - 60, -0.0755148492);
    b = 255;
  }
  auto clamp = [](float v) { return (uint8_t)constrain((int)v, 0, 255); };
  return Adafruit_NeoPixel::Color(clamp(r), clamp(g), clamp(b));
}

uint16_t matrixIndex(uint8_t x, uint8_t y) {
  if (x >= MATRIX_WIDTH || y >= MATRIX_HEIGHT) return 0;
  // Serpentine layout assumed: even rows L->R, odd rows R->L.
  if (y % 2 == 0) {
    return y * MATRIX_WIDTH + x;
  } else {
    return y * MATRIX_WIDTH + (MATRIX_WIDTH - 1 - x);
  }
}

void fillAll(uint32_t color) {
  for (uint8_t i = 0; i < STRIP_COUNT; i++) {
    for (uint16_t p = 0; p < STRIP_LENGTHS[i]; p++) {
      strips[i].setPixelColor(p, color);
    }
    strips[i].show();
  }
}

void beginWifi() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // keep radio responsive for pings
  WiFi.setAutoReconnect(true);
  WiFi.setTxPower(WIFI_POWER_19_5dBm);
  // Fresh connect (DHCP only), with BSSID lock first then open scan.
  auto try_ssid = [](const char *ssid, const char *pass, const uint8_t *bssid, int channel) {
    if (bssid) {
      Serial.printf("Trying SSID: %s (locked BSSID)\n", ssid);
    } else {
      Serial.printf("Trying SSID: %s (open scan)\n", ssid);
    }
    WiFi.disconnect(true, true);
    delay(200);
    WiFi.begin(ssid, pass, channel, bssid, true);
    uint8_t tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 60) {  // ~30s
      delay(500);
      Serial.print(".");
      tries++;
    }
    Serial.println();
    return WiFi.status() == WL_CONNECTED;
  };

  bool ok = try_ssid(WIFI1_SSID, WIFI1_PASS, AP_BSSID, AP_CHANNEL);
  if (!ok) {
    Serial.println("Lock failed, retrying without BSSID/channel...");
    ok = try_ssid(WIFI1_SSID, WIFI1_PASS, nullptr, 0);
  }
  if (!ok) ok = try_ssid(WIFI2_SSID, WIFI2_PASS, nullptr, 0);

  Serial.print("WiFi status after begin: ");
  Serial.print(WiFi.status());
  Serial.print(" (");
  Serial.print(wifiStatusText(WiFi.status()));
  Serial.println(")");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("RSSI: ");
  Serial.println(WiFi.RSSI());
}

void mqttCallback(char *topic, byte *payload, unsigned int length) {
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) return;
  const char *cmd = doc["cmd"] | "";
  if (strcmp(cmd, "set") != 0) return;
  if (doc.containsKey("pattern")) {
    String p = String(doc["pattern"].as<const char *>());
    p.toLowerCase();
    if (p == "solid") p = "white";
    if (p == "rainbow_hills") {
      state.pattern = "rainbow_hills";
    } else if (p == "rainbow") {
      state.pattern = "rainbow";
    } else {
      state.pattern = "white";
    }
  }
  if (doc.containsKey("brightness")) state.brightness = doc["brightness"].as<float>();
  if (doc.containsKey("white_balance")) state.whiteBalance = doc["white_balance"].as<float>();
  if (doc.containsKey("color") && doc["color"].is<JsonArray>()) {
    JsonArray arr = doc["color"].as<JsonArray>();
    if (arr.size() >= 3) {
      state.color[0] = (uint8_t)arr[0].as<int>();
      state.color[1] = (uint8_t)arr[1].as<int>();
      state.color[2] = (uint8_t)arr[2].as<int>();
      state.hasColor = true;
    } else {
      state.hasColor = false;
    }
  } else {
    state.hasColor = false;
  }
  Serial.printf("MQTT set: pattern=%s brightness=%.1f wb=%.1f hasColor=%d\n",
                state.pattern.c_str(), state.brightness, state.whiteBalance, state.hasColor);
  state.lastUpdate = millis();
  applyPatternNow();
}

void ensureMqtt() {
  if (mqtt.connected()) return;
  if (WiFi.status() != WL_CONNECTED) {
    beginWifi();
  }
  while (!mqtt.connected()) {
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
    mqtt.setCallback(mqttCallback);
    if (mqtt.connect("esp32u-camming", MQTT_USER, MQTT_PASS)) {
      mqtt.subscribe(MQTT_CMD_TOPIC);
      StaticJsonDocument<64> doc;
      doc["status"] = "online";
      char buf[64];
      size_t n = serializeJson(doc, buf);
      mqtt.publish(MQTT_STATUS_TOPIC, buf, n);
      Serial.println("MQTT connected");
      break;
    }
    Serial.println("MQTT connect failed, retrying...");
    delay(1000);
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("ESP32U camming boot");
  for (uint8_t i = 0; i < STRIP_COUNT; i++) {
    strips[i].begin();
    strips[i].setBrightness(255);
    strips[i].clear();
    strips[i].show();
  }
  beginWifi();
  // OTA: enable for on-network updates once connected.
  ArduinoOTA.setHostname("esp32u-camming");
  ArduinoOTA
      .onStart([]() { Serial.println("OTA start"); })
      .onEnd([]() { Serial.println("\nOTA end"); })
      .onProgress([](unsigned int prog, unsigned int total) {
        Serial.printf("OTA progress: %u%%\n", (prog * 100) / total);
      })
      .onError([](ota_error_t err) {
        Serial.printf("OTA error [%u]\n", err);
      });
  ArduinoOTA.begin();
  ensureMqtt();
  Serial.println("MQTT ensured");
  applyPatternNow();
}

void loop() {
  ArduinoOTA.handle();
  ensureMqtt();
  mqtt.loop();
  static unsigned long lastStatus = 0;
  if (millis() - lastStatus > 5000 && mqtt.connected()) {
    StaticJsonDocument<64> doc;
    doc["status"] = "online";
    doc["ip"] = WiFi.localIP().toString();
    doc["rssi"] = WiFi.RSSI();
    char buf[64];
    size_t n = serializeJson(doc, buf);
    mqtt.publish(MQTT_STATUS_TOPIC, reinterpret_cast<const uint8_t *>(buf), n, true);
    lastStatus = millis();
  }
  unsigned long now = millis();
  float dt = (state.lastUpdate == 0) ? 0.02f : (now - state.lastUpdate) / 1000.0f;
  state.lastUpdate = now;
  if (state.pattern == "rainbow") {
    renderRainbow(dt);
  }
  delay(10);
}

void applyPatternNow() {
  Serial.printf("Apply pattern: %s brightness=%.1f wb=%.1f hasColor=%d rgb=(%u,%u,%u)\n",
                state.pattern.c_str(), state.brightness, state.whiteBalance, state.hasColor,
                state.color[0], state.color[1], state.color[2]);
  if (state.pattern == "white") {
    uint32_t base = Adafruit_NeoPixel::Color(state.color[0], state.color[1], state.color[2]);
    if (!state.hasColor) {
      base = colorTempToRGB(state.whiteBalance);
    }
    if (base == 0) {
      base = Adafruit_NeoPixel::Color(255, 255, 255);  // fail-safe solid white
    }
    uint8_t b = (uint8_t)constrain((int)state.brightness, 0, 255);
    for (uint8_t i = 0; i < STRIP_COUNT; i++) {
      strips[i].setBrightness(b);
      for (uint16_t p = 0; p < STRIP_LENGTHS[i]; p++) {
        strips[i].setPixelColor(p, base);
      }
      strips[i].show();
    }
  } else if (state.pattern == "rainbow") {
    // renderRainbow() will animate in loop
    renderRainbow(0.0f);
  } else if (state.pattern == "rainbow_hills") {
    // renderRainbowHills() will animate in loop
    renderRainbowHills(0.0f);
  } else {
    // Fallback to white if unknown
    state.pattern = "white";
    applyPatternNow();
  }
}

void renderRainbow(float dt) {
  state.rainbowPhase += dt * 60.0f;
  for (uint8_t i = 0; i < STRIP_COUNT; i++) {
    for (uint16_t p = 0; p < STRIP_LENGTHS[i]; p++) {
      uint8_t pos = (uint8_t)((p * 256UL / STRIP_LENGTHS[i]) + (uint16_t)state.rainbowPhase) & 0xFF;
      uint32_t c = Adafruit_NeoPixel::ColorHSV(pos * 256, 255, 255);
      strips[i].setPixelColor(p, strips[i].gamma32(c));
    }
    strips[i].setBrightness((uint8_t)constrain((int)state.brightness, 0, 255));
    strips[i].show();
  }
}

void renderRainbowHills(float dt) {
  // Multiple short rainbows with a soft brightness envelope per hill.
  state.rainbowPhase += dt * 12.0f;  // slower drift
  for (uint8_t i = 0; i < STRIP_COUNT; i++) {
    uint16_t len = STRIP_LENGTHS[i];
    float hills = 6.0f;                 // number of rainbow hills along the strip
    float hillLen = (float)len / hills; // pixels per hill
    for (uint16_t p = 0; p < len; p++) {
      float pos = (float)p + state.rainbowPhase * 0.6f;  // scroll
      float local = fmodf(pos, hillLen) / hillLen;       // 0..1 within hill
      float envelope = sinf(local * PI);                 // fade up/down per hill
      // shape envelope to keep center brighter but soft edges
      envelope = powf(envelope, 1.2f);
      uint8_t hue = (uint8_t)(local * 255.0f);
      uint32_t c = Adafruit_NeoPixel::ColorHSV(hue * 256, 255, (uint8_t)(255 * envelope));
      strips[i].setPixelColor(p, strips[i].gamma32(c));
    }
    strips[i].setBrightness((uint8_t)constrain((int)state.brightness, 0, 255));
    strips[i].show();
  }
}

void drawPoint(uint8_t x, uint8_t y, uint32_t color) {
  uint16_t idx = matrixIndex(x, y);
  if (idx < MATRIX_LENGTH) {
    strips[0].setPixelColor(idx, color);
  }
}

void clearMatrix(uint32_t color = 0) {
  for (uint16_t i = 0; i < MATRIX_LENGTH; i++) {
    strips[0].setPixelColor(i, color);
  }
}

void renderMatrixSmiley(uint32_t fg, uint32_t bg) {
  clearMatrix(bg);
  for (uint8_t y = 3; y <= 9; y++) {
    for (uint8_t x = 4; x <= 18; x++) {
      drawPoint(x, y, fg);
    }
  }
  // Eyes
  drawPoint(8, 5, 0);
  drawPoint(14, 5, 0);
  // Mouth
  for (uint8_t x = 8; x <= 14; x++) drawPoint(x, 9, 0);
  drawPoint(7, 8, 0);
  drawPoint(15, 8, 0);
}

void renderMatrixDancer(uint32_t color, uint32_t bg, bool pose) {
  clearMatrix(bg);
  // head
  drawPoint(11, 2, color);
  // arms
  drawPoint(10, 4, color);
  drawPoint(12, 4, color);
  drawPoint(pose ? 9 : 13, 4, color);
  // body
  drawPoint(11, 5, color);
  drawPoint(11, 6, color);
  drawPoint(11, 7, color);
  // legs
  drawPoint(10, 9, color);
  drawPoint(12, 9, color);
  drawPoint(pose ? 9 : 13, 10, color);
}

void renderMatrixFireworks(uint32_t color, uint32_t bg, float t) {
  clearMatrix(bg);
  randomSeed((uint32_t)(micros() + t * 1000));
  for (uint8_t i = 0; i < 20; i++) {
    drawPoint(random(0, MATRIX_WIDTH), random(0, MATRIX_HEIGHT), color);
  }
}

void renderMatrixWaves(uint32_t color, uint32_t bg, float t) {
  clearMatrix(bg);
  for (uint8_t x = 0; x < MATRIX_WIDTH; x++) {
    float yf = (sinf(t * 2.0f + x * 0.5f) + 1.0f) * 0.5f * (MATRIX_HEIGHT - 1);
    uint8_t y = (uint8_t)yf;
    drawPoint(x, y, color);
  }
}
