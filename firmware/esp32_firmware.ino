#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoOTA.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>
#include <PubSubClient.h>
#include <HTTPClient.h>
#include <Update.h>
#include <driver/i2s.h>

// Wi-Fi credentials (current AP)
const char *WIFI1_SSID = "trannyfix";
const char *WIFI1_PASS = "transgender";
const char *WIFI2_SSID = "trannyfix";
const char *WIFI2_PASS = "transgender";

// MQTT broker (AP LAN)
const char *MQTT_HOST = "10.42.0.1";
constexpr uint16_t MQTT_PORT = 1883;
const char *MQTT_USER = "";  // optional
const char *MQTT_PASS = "";  // optional
const char *MQTT_CMD_TOPIC = "led/command";
const char *MQTT_STATUS_TOPIC = "led/status";
const char *TEST_OTA_URL = "http://192.168.12.157:8000/http_ota.bin";
const char *FW_VERSION = "fw-ota-trannyfix";
constexpr bool DO_BOOT_HTTP_OTA = false;

// Strip wiring: pins and lengths, in physical order along the run.
constexpr uint8_t STRIP_COUNT = 4;
constexpr uint8_t STRIP_PINS[STRIP_COUNT] = {9, 10, 11, 47};
// Main surround strip (pin 10) extended by +300 LEDs (was 200 -> now 500).
constexpr uint16_t STRIP_LENGTHS[STRIP_COUNT] = {50, 500, 80, 80};
constexpr neoPixelType LED_TYPE = NEO_GRB + NEO_KHZ800;

// Segment definitions using global indices (0-based across all strips).
// Total length = 410 (50 + 200 + 80 + 80).
// Segment names exposed to MQTT/web UI.
struct SegmentDef {
  const char *name;
  uint16_t start;   // global index
  uint16_t length;
  uint8_t stripIdx;
  uint16_t stripOffset;  // start within the owning strip
};

constexpr uint16_t TOTAL_LEDS =
    STRIP_LENGTHS[0] + STRIP_LENGTHS[1] + STRIP_LENGTHS[2] + STRIP_LENGTHS[3];

SegmentDef SEGMENTS[] = {
    {"strip0", 0, STRIP_LENGTHS[0], 0, 0},
    {"strip1", STRIP_LENGTHS[0], STRIP_LENGTHS[1], 1, 0},
    {"strip2", STRIP_LENGTHS[0] + STRIP_LENGTHS[1], STRIP_LENGTHS[2], 2, 0},
    {"strip3", STRIP_LENGTHS[0] + STRIP_LENGTHS[1] + STRIP_LENGTHS[2], STRIP_LENGTHS[3], 3, 0},
    // Speaker segments now reside within the extended main surround strip (pin 10).
    {"seg250_323", 250, 74, 1, 250 - STRIP_LENGTHS[0]},   // within strip1
    {"seg330_400", 330, 71, 1, 330 - STRIP_LENGTHS[0]},   // within strip1
};
constexpr size_t SEGMENT_COUNT = sizeof(SEGMENTS) / sizeof(SEGMENTS[0]);

constexpr float DEFAULT_BRIGHTNESS = 200.0f;  // OTA test bump (0-255 scale)
constexpr float DEFAULT_SPEED = 1.0f;
constexpr float DEFAULT_MIC_GAIN = 0.3f;
constexpr float DEFAULT_MIC_FLOOR = 0.02f;
constexpr float DEFAULT_MIC_SMOOTH = 0.30f;

// I2S microphone pins
constexpr i2s_port_t MIC_PORT = I2S_NUM_0;
constexpr int MIC_PIN_BCLK = 4;
constexpr int MIC_PIN_WS = 6;
constexpr int MIC_PIN_DATA = 5;
constexpr int MIC_SAMPLE_RATE = 16000;
constexpr size_t MIC_BUF_SAMPLES = 256;  // small buffer for low latency

struct SegmentState {
  String pattern = "solid";
  float brightness = DEFAULT_BRIGHTNESS;
  float speed = DEFAULT_SPEED;
  float windMph = 0.0f;
  uint8_t color[3] = {0, 180, 160};
  String waveShape = "sine";
  float waves = 1.0f;  // for rainbow density
  float micGain = DEFAULT_MIC_GAIN;
  float micFloor = DEFAULT_MIC_FLOOR;
  float micSmooth = DEFAULT_MIC_SMOOTH;
  bool micEnabled = true;
  bool gradientEnabled = false;
  uint8_t gradLow[3] = {0, 120, 255};
  uint8_t gradMid[3] = {255, 255, 255};
  uint8_t gradHigh[3] = {255, 0, 120};
  bool beatMode = false;
};

struct SegmentRuntime {
  float rainbowPhase = 0.0f;
  float sinePhase = 0.0f;
  float micValue = 0.0f;
  float beatHold = 0.0f;  // seconds of full-on after a detected beat
};

Adafruit_NeoPixel strips[STRIP_COUNT] = {
    Adafruit_NeoPixel(STRIP_LENGTHS[0], STRIP_PINS[0], LED_TYPE),
    Adafruit_NeoPixel(STRIP_LENGTHS[1], STRIP_PINS[1], LED_TYPE),
    Adafruit_NeoPixel(STRIP_LENGTHS[2], STRIP_PINS[2], LED_TYPE),
    Adafruit_NeoPixel(STRIP_LENGTHS[3], STRIP_PINS[3], LED_TYPE),
};

SegmentState segmentStates[SEGMENT_COUNT];
SegmentRuntime segmentRuntime[SEGMENT_COUNT];

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

uint32_t lastWifiCheck = 0;
float micLevel = 0.0f;          // smoothed 0..1
float micRawLevel = 0.0f;       // instantaneous 0..1
bool micReady = false;

// Helpers -------------------------------------------------------------------
float clamp01(float v) {
  if (v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

uint32_t lerp_color(const uint8_t a[3], const uint8_t b[3], float t) {
  t = clamp01(t);
  uint8_t r = static_cast<uint8_t>(a[0] + (b[0] - a[0]) * t);
  uint8_t g = static_cast<uint8_t>(a[1] + (b[1] - a[1]) * t);
  uint8_t bch = static_cast<uint8_t>(a[2] + (b[2] - a[2]) * t);
  return Adafruit_NeoPixel::Color(r, g, bch);
}

float clamp_brightness(float v) {
  if (v < 0.0f) return 0.0f;
  if (v > 255.0f) return 255.0f;
  return v;
}

uint32_t wheel(uint8_t pos) {
  pos = 255 - pos;
  if (pos < 85) {
    return Adafruit_NeoPixel::Color(255 - pos * 3, 0, pos * 3);
  }
  if (pos < 170) {
    pos -= 85;
    return Adafruit_NeoPixel::Color(0, pos * 3, 255 - pos * 3);
  }
  pos -= 170;
  return Adafruit_NeoPixel::Color(pos * 3, 255 - pos * 3, 0);
}

uint32_t scale_color(uint32_t color, float brightness255) {
  float brightness = clamp01(brightness255 / 255.0f);
  uint8_t r = (color >> 16) & 0xFF;
  uint8_t g = (color >> 8) & 0xFF;
  uint8_t b = color & 0xFF;
  r = static_cast<uint8_t>(r * brightness);
  g = static_cast<uint8_t>(g * brightness);
  b = static_cast<uint8_t>(b * brightness);
  return Adafruit_NeoPixel::Color(r, g, b);
}

int find_segment_index(const String &name) {
  for (size_t i = 0; i < SEGMENT_COUNT; i++) {
    if (name == SEGMENTS[i].name) return static_cast<int>(i);
  }
  return -1;
}

// Rendering -----------------------------------------------------------------
float shape_wave(const SegmentState &st, float x) {
  if (st.waveShape == "square") {
    return x < PI ? 1.0f : -1.0f;
  }
  if (st.waveShape == "triangle") {
    float saw = (x / (2 * PI));
    saw = saw - floor(saw);
    float tri = saw < 0.5f ? saw * 2.0f : (1.0f - saw) * 2.0f;
    return tri * 2.0f - 1.0f;
  }
  return sinf(x);
}

void render_segment(size_t idx, float dt) {
  const SegmentDef &seg = SEGMENTS[idx];
  SegmentState &st = segmentStates[idx];
  SegmentRuntime &rt = segmentRuntime[idx];
  Adafruit_NeoPixel &strip = strips[seg.stripIdx];

  if (st.pattern == "rainbow") {
    rt.rainbowPhase += dt * 60.0f * clamp01(st.speed);
    float waves = st.waves;
    if (waves < 1.0f) waves = 1.0f;
    for (uint16_t i = 0; i < seg.length; i++) {
      uint8_t pos = (static_cast<uint32_t>(i * 256 * waves / seg.length + static_cast<uint16_t>(rt.rainbowPhase))) & 0xFF;
      uint32_t c = wheel(pos);
      strip.setPixelColor(seg.stripOffset + i, scale_color(c, st.brightness));
    }
  } else if (st.pattern == "sine") {
    rt.sinePhase += dt * 4.0f * clamp01(st.speed);
    float bf = clamp01(st.brightness / 255.0f);
    for (uint16_t i = 0; i < seg.length; i++) {
      float pos = (static_cast<float>(i) / seg.length) * 2.0f * PI;
      float v = shape_wave(st, pos + rt.sinePhase);
      float k = (v + 1.0f) * 0.5f;
      uint8_t r = static_cast<uint8_t>(st.color[0] * k * bf);
      uint8_t g = static_cast<uint8_t>(st.color[1] * k * bf);
      uint8_t b = static_cast<uint8_t>(st.color[2] * k * bf);
      strip.setPixelColor(seg.stripOffset + i, strip.Color(r, g, b));
    }
  } else if (st.pattern == "wind_meter") {
    uint16_t lit = static_cast<uint16_t>(roundf(st.windMph));
    if (lit > seg.length) lit = seg.length;
    float bf = clamp01(st.brightness / 255.0f);
    for (uint16_t i = 0; i < seg.length; i++) {
      if (i < lit) {
        float t = static_cast<float>(i) / max<uint16_t>(1, seg.length - 1);
        uint8_t r = static_cast<uint8_t>(255 * (1.0f - t) * bf);
        uint8_t g = static_cast<uint8_t>(255 * t * bf);
        strip.setPixelColor(seg.stripOffset + i, strip.Color(r, g, 0));
      } else {
        strip.setPixelColor(seg.stripOffset + i, 0);
      }
    }
  } else if (st.pattern == "mic_vu") {
    // Simple VU meter driven by micLevel.
    float val = st.micEnabled ? micLevel : 0.0f;
    // Per-segment smoothing layer.
    rt.micValue = rt.micValue * st.micSmooth + val * (1.0f - st.micSmooth);
    float v = (rt.micValue - st.micFloor) * st.micGain;
    if (v < 0.0f) v = 0.0f;
    v = clamp01(v);
    // Beat detect: simple threshold + cooldown hold.
    const float beatThresh = 0.45f;
    const float beatHoldSeconds = 0.18f;
    if (st.beatMode) {
      if (v > beatThresh && rt.beatHold <= 0.0f) {
        rt.beatHold = beatHoldSeconds;
      }
      if (rt.beatHold > 0.0f) {
        v = 1.0f;
        rt.beatHold -= dt;
        if (rt.beatHold < 0.0f) rt.beatHold = 0.0f;
      }
    }
    uint16_t lit = static_cast<uint16_t>(roundf(v * seg.length));
    for (uint16_t i = 0; i < seg.length; i++) {
      if (i < lit) {
        uint32_t c;
        if (st.gradientEnabled) {
          float t = seg.length > 1 ? static_cast<float>(i) / (seg.length - 1) : 0.0f;
          if (t < 0.5f) {
            c = lerp_color(st.gradLow, st.gradMid, t * 2.0f);
          } else {
            c = lerp_color(st.gradMid, st.gradHigh, (t - 0.5f) * 2.0f);
          }
        } else {
          c = strip.Color(st.color[0], st.color[1], st.color[2]);
        }
        strip.setPixelColor(seg.stripOffset + i, scale_color(c, st.brightness));
      } else {
        strip.setPixelColor(seg.stripOffset + i, 0);
      }
    }
  } else {  // solid
    uint32_t base = strip.Color(st.color[0], st.color[1], st.color[2]);
    uint32_t c = scale_color(base, st.brightness);
    for (uint16_t i = 0; i < seg.length; i++) {
      strip.setPixelColor(seg.stripOffset + i, c);
    }
  }
}

void render_all(float dt) {
  // Clear all strips first.
  for (uint8_t s = 0; s < STRIP_COUNT; s++) {
    for (uint16_t i = 0; i < STRIP_LENGTHS[s]; i++) {
      strips[s].setPixelColor(i, 0);
    }
  }
  // Draw each segment with its own state.
  for (size_t i = 0; i < SEGMENT_COUNT; i++) {
    render_segment(i, dt);
  }
  for (uint8_t s = 0; s < STRIP_COUNT; s++) {
    strips[s].show();
  }
}

// Command handling ----------------------------------------------------------
void apply_params(SegmentState &st, JsonVariant params) {
  if (params.isNull()) return;
  if (params.containsKey("color")) {
    JsonArray arr = params["color"].as<JsonArray>();
    if (arr.size() == 3) {
      st.color[0] = constrain(arr[0].as<int>(), 0, 255);
      st.color[1] = constrain(arr[1].as<int>(), 0, 255);
      st.color[2] = constrain(arr[2].as<int>(), 0, 255);
    }
    st.gradientEnabled = false;  // explicit color disables gradient unless re-set below
  }
  if (params.containsKey("wave_shape")) {
    st.waveShape = String(params["wave_shape"].as<const char *>());
  }
  if (params.containsKey("wind_mph")) {
    st.windMph = params["wind_mph"].as<float>();
  }
  if (params.containsKey("wave_count")) {
    st.waves = params["wave_count"].as<float>();
    if (st.waves < 0.0f) st.waves = 0.0f;
  }
  if (params.containsKey("mic_gain")) {
    st.micGain = params["mic_gain"].as<float>();
  }
  if (params.containsKey("mic_floor")) {
    st.micFloor = params["mic_floor"].as<float>();
  }
  if (params.containsKey("mic_smooth")) {
    st.micSmooth = params["mic_smooth"].as<float>();
    if (st.micSmooth < 0.0f) st.micSmooth = 0.0f;
    if (st.micSmooth > 0.6f) st.micSmooth = 0.6f;
  }
  if (params.containsKey("mic_enabled")) {
    st.micEnabled = params["mic_enabled"].as<bool>();
  }
  if (params.containsKey("mic_beat")) {
    st.beatMode = params["mic_beat"].as<bool>();
  }
  if (params.containsKey("gradient_low")) {
    JsonArray arr = params["gradient_low"].as<JsonArray>();
    if (arr.size() == 3) {
      st.gradLow[0] = constrain(arr[0].as<int>(), 0, 255);
      st.gradLow[1] = constrain(arr[1].as<int>(), 0, 255);
      st.gradLow[2] = constrain(arr[2].as<int>(), 0, 255);
      st.gradientEnabled = true;
    }
  }
  if (params.containsKey("gradient_mid")) {
    JsonArray arr = params["gradient_mid"].as<JsonArray>();
    if (arr.size() == 3) {
      st.gradMid[0] = constrain(arr[0].as<int>(), 0, 255);
      st.gradMid[1] = constrain(arr[1].as<int>(), 0, 255);
      st.gradMid[2] = constrain(arr[2].as<int>(), 0, 255);
      st.gradientEnabled = true;
    }
  }
  if (params.containsKey("gradient_high")) {
    JsonArray arr = params["gradient_high"].as<JsonArray>();
    if (arr.size() == 3) {
      st.gradHigh[0] = constrain(arr[0].as<int>(), 0, 255);
      st.gradHigh[1] = constrain(arr[1].as<int>(), 0, 255);
      st.gradHigh[2] = constrain(arr[2].as<int>(), 0, 255);
      st.gradientEnabled = true;
    }
  }
  if (params.containsKey("gradient_enabled")) {
    st.gradientEnabled = params["gradient_enabled"].as<bool>();
  }
}

// HTTP OTA ------------------------------------------------------------------
bool http_ota_update(const String &url) {
  Serial.printf("HTTP OTA: fetching %s\n", url.c_str());
  HTTPClient http;
  http.setReuse(false);
  http.setTimeout(20000);
  http.begin(url);
  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    Serial.printf("HTTP OTA failed, code %d\n", code);
    http.end();
    return false;
  }
  int len = http.getSize();
  Serial.printf("HTTP OTA size: %d bytes\n", len);
  WiFiClient *stream = http.getStreamPtr();
  if (len <= 0) {
    Serial.println("HTTP OTA invalid length");
    http.end();
    return false;
  }
  if (!Update.begin(len)) {
    Serial.println("Update.begin failed");
    http.end();
    return false;
  }
  const size_t buf_size = 2048;
  uint8_t buf[buf_size];
  size_t total = 0;
  while (http.connected() && total < (size_t)len) {
    size_t avail = stream->available();
    if (avail) {
      size_t rd = stream->readBytes(buf, avail > buf_size ? buf_size : avail);
      if (rd > 0) {
        size_t w = Update.write(buf, rd);
        total += w;
      }
    } else {
      delay(1);
    }
  }
  Serial.printf("Update wrote %u/%d bytes\n", (unsigned)total, len);
  bool ok = Update.end();
  http.end();
  if (!ok || Update.hasError()) {
    Serial.printf("Update failed: %s\n", Update.errorString());
    Update.printError(Serial);
    return false;
  }
  Serial.println("HTTP OTA success, restarting...");
  delay(500);
  ESP.restart();
  return true;  // not reached
}

void handle_command(JsonDocument &doc) {
  const char *cmd = doc["cmd"] | "";
  String segName = doc["segment"] | "strip1";  // default to main long strip
  int segIdx = find_segment_index(segName);
  if (segIdx < 0) {
    mqtt.publish(MQTT_STATUS_TOPIC, "{\"error\":\"bad_segment\"}", false);
    return;
  }
  SegmentState &st = segmentStates[segIdx];

  if (strcmp(cmd, "set") == 0) {
    if (doc.containsKey("pattern")) {
      st.pattern = String(doc["pattern"].as<const char *>());
    }
    if (doc.containsKey("brightness")) {
      st.brightness = clamp_brightness(doc["brightness"].as<float>());
    }
    if (doc.containsKey("speed")) {
      st.speed = doc["speed"].as<float>();
    }
    JsonVariant params = doc["params"];
    apply_params(st, params);
  } else if (strcmp(cmd, "ping") == 0) {
    mqtt.publish(MQTT_STATUS_TOPIC, "{\"pong\":true}", false);
  } else if (strcmp(cmd, "ota_http") == 0) {
    String url = doc["url"] | "";
    if (url.length() == 0) {
      mqtt.publish(MQTT_STATUS_TOPIC, "{\"ota\":\"missing_url\"}", false);
    } else {
      mqtt.publish(MQTT_STATUS_TOPIC, "{\"ota\":\"starting\"}", false);
      http_ota_update(url);
      // If it returns, it failed.
      mqtt.publish(MQTT_STATUS_TOPIC, "{\"ota\":\"failed\"}", false);
    }
  }
}

void on_mqtt_message(char *topic, byte *payload, unsigned int length) {
  if (length == 0 || length > 512) return;
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.println("MQTT JSON parse error");
    return;
  }
  Serial.print("MQTT cmd: ");
  serializeJson(doc, Serial);
  Serial.println();
  handle_command(doc);
}

// Connectivity --------------------------------------------------------------
void connect_wifi() {
  Serial.println("Booting... Wi-Fi setup start");
  WiFi.mode(WIFI_STA);
  WiFi.config(INADDR_NONE, INADDR_NONE, INADDR_NONE);  // DHCP

  auto try_ssid = [](const char *ssid, const char *pass) {
    Serial.printf("Trying SSID: %s\n", ssid);
    WiFi.begin(ssid, pass);
    uint8_t tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 60) {
      delay(500);
      Serial.print(".");
      tries++;
    }
    Serial.println();
    return WiFi.status() == WL_CONNECTED;
  };

  bool ok = try_ssid(WIFI1_SSID, WIFI1_PASS);
  if (!ok) {
    ok = try_ssid(WIFI2_SSID, WIFI2_PASS);
  }
  if (ok) {
    Serial.printf("Connected, IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("Wi-Fi connect failed, staying in loop");
  }
}

void setup_ota() {
  ArduinoOTA.setHostname("esp32-led-engine");
  ArduinoOTA.setPort(3232);
  ArduinoOTA.onStart([]() { Serial.println("OTA start"); });
  ArduinoOTA.onEnd([]() { Serial.println("OTA end"); });
  ArduinoOTA.onError([](ota_error_t err) { Serial.printf("OTA Error %u\n", err); });
  ArduinoOTA.begin();
  Serial.println("OTA ready on port 3232");
}

void mqtt_reconnect() {
  while (!mqtt.connected()) {
    String mac = WiFi.macAddress();
    mac.replace(":", "");
    String clientId = "esp32-led-engine-" + mac;
    Serial.println("MQTT reconnect...");
    bool ok;
    if (strlen(MQTT_USER) > 0) {
      ok = mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS);
    } else {
      ok = mqtt.connect(clientId.c_str());
    }
    if (ok) {
      Serial.println("MQTT connected");
      mqtt.subscribe(MQTT_CMD_TOPIC);
      mqtt.publish(MQTT_STATUS_TOPIC, "{\"status\":\"online\"}", false);
      break;
    }
    Serial.printf("MQTT connect failed rc=%d, retrying...\n", mqtt.state());
    delay(500);
  }
}

// Microphone ---------------------------------------------------------------
void setup_mic() {
  i2s_config_t cfg = {
      .mode = static_cast<i2s_mode_t>(I2S_MODE_MASTER | I2S_MODE_RX),
      .sample_rate = MIC_SAMPLE_RATE,
      .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
      .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
      .communication_format = I2S_COMM_FORMAT_STAND_I2S,
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 4,
      .dma_buf_len = static_cast<int>(MIC_BUF_SAMPLES),
      .use_apll = false,
      .tx_desc_auto_clear = false,
      .fixed_mclk = 0,
      .mclk_multiple = I2S_MCLK_MULTIPLE_256,
      .bits_per_chan = I2S_BITS_PER_CHAN_32BIT
  };
  i2s_pin_config_t pins = {
      .bck_io_num = MIC_PIN_BCLK,
      .ws_io_num = MIC_PIN_WS,
      .data_out_num = I2S_PIN_NO_CHANGE,
      .data_in_num = MIC_PIN_DATA,
  };
  if (i2s_driver_install(MIC_PORT, &cfg, 0, nullptr) == ESP_OK) {
    if (i2s_set_pin(MIC_PORT, &pins) == ESP_OK) {
      micReady = true;
      Serial.println("Mic: I2S ready");
    } else {
      Serial.println("Mic: pin set failed");
    }
  } else {
    Serial.println("Mic: driver install failed");
  }
}

void read_mic_level() {
  if (!micReady) return;
  int32_t buf[MIC_BUF_SAMPLES] = {0};
  size_t bytes_read = 0;
  esp_err_t res = i2s_read(MIC_PORT, buf, sizeof(buf), &bytes_read, 0);
  if (res != ESP_OK || bytes_read == 0) return;
  size_t samples = bytes_read / sizeof(int32_t);
  if (samples == 0) return;
  double acc = 0.0;
  for (size_t i = 0; i < samples; i++) {
    acc += fabs(static_cast<double>(buf[i]));
  }
  double avg = acc / samples;
  // Normalize roughly to 0..1 assuming 24-bit data in 32-bit container.
  double norm = avg / 8388608.0;  // 2^23
  if (norm > 1.5) norm = 1.5;     // clamp extreme spikes
  micRawLevel = static_cast<float>(norm);
  // Global smoothing
  micLevel = micLevel * DEFAULT_MIC_SMOOTH + micRawLevel * (1.0f - DEFAULT_MIC_SMOOTH);
}

// Setup/loop ----------------------------------------------------------------
uint32_t lastMillis = 0;

void setup() {
  Serial.begin(115200);
  Serial.printf("Firmware: %s\n", FW_VERSION);
  for (uint8_t i = 0; i < STRIP_COUNT; i++) {
    strips[i].begin();
    strips[i].setBrightness(255);
    strips[i].show();
  }
  setup_mic();
  connect_wifi();
  if (DO_BOOT_HTTP_OTA) {
    if (!http_ota_update(TEST_OTA_URL)) {
      Serial.println("HTTP OTA failed (boot test)");
    }
  }
  setup_ota();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(on_mqtt_message);
  mqtt.setBufferSize(512);
  mqtt_reconnect();
  lastMillis = millis();
}

void loop() {
  // Wi-Fi keepalive
  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiCheck > 3000) {
    connect_wifi();
    lastWifiCheck = millis();
  }

  ArduinoOTA.handle();
  if (!mqtt.connected()) {
    mqtt_reconnect();
  }
  mqtt.loop();

  uint32_t now = millis();
  float dt = (now - lastMillis) / 1000.0f;
  if (dt < 0) dt = 0;
  if (dt > 0.05f) dt = 0.05f;  // clamp large jumps
  lastMillis = now;

  read_mic_level();
  render_all(dt);
  delay(10);  // ~100 FPS cap
}
