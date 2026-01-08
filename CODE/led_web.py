"""
Local web UI to control ESP32 LED segments via MQTT.
- Serves a colorful, mobile-friendly page with segment controls.
- Exposes status endpoint used by the page.
Run: source .env.mqtt && python3 led_web.py
"""
from __future__ import annotations

import json
import os
import time
import subprocess
import math
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

from flask import Flask, jsonify, render_template_string, request
import paho.mqtt.client as mqtt
import requests
from templates import HTML

MQTT_HOST = os.getenv("MQTT_HOST", "10.42.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER") or None
MQTT_PASS = os.getenv("MQTT_PASS") or None
MQTT_CMD_TOPIC = os.getenv("MQTT_CMD_TOPIC", "led/command")
STATES_FILE = os.getenv("LED_STATE_FILE", os.path.join(os.path.dirname(__file__), "led_states.json"))
WEATHER_CACHE_FILE = os.getenv("WEATHER_CACHE_FILE", os.path.join(os.path.dirname(__file__), "weather_cache.json"))
SEGMENTS = [
    "strip0",
    "strip1",
    "strip2",
    "strip3",
]
SEGMENT_LABELS = {
    "strip1": "Main Surround Lights",
    "strip2": "Right Speaker",
    "strip3": "Left Speaker",
}
PATTERNS = ["solid", "rainbow", "sine", "wind_meter", "mic_vu"]
CAMMING_PATTERNS = ["white", "rainbow", "rainbow_hills"]
COLOR_PALETTE = [
    ("Red", [255, 0, 0]),
    ("Crimson", [220, 20, 60]),
    ("Dark Red", [139, 0, 0]),
    ("Coral", [255, 127, 80]),
    ("Tomato", [255, 99, 71]),
    ("Orange Red", [255, 69, 0]),
    ("Orange", [255, 165, 0]),
    ("Gold", [255, 215, 0]),
    ("Yellow", [255, 255, 0]),
    ("Olive", [128, 128, 0]),
    ("Lime", [0, 255, 0]),
    ("Lime Green", [50, 205, 50]),
    ("Spring Green", [0, 255, 127]),
    ("Sea Green", [46, 139, 87]),
    ("Forest Green", [34, 139, 34]),
    ("Teal", [0, 128, 128]),
    ("Turquoise", [64, 224, 208]),
    ("Light Sea Green", [32, 178, 170]),
    ("Cyan", [0, 255, 255]),
    ("Deep Sky Blue", [0, 191, 255]),
    ("Sky Blue", [135, 206, 235]),
    ("Steel Blue", [70, 130, 180]),
    ("Dodger Blue", [30, 144, 255]),
    ("Royal Blue", [65, 105, 225]),
    ("Blue", [0, 0, 255]),
    ("Medium Blue", [0, 0, 205]),
    ("Navy", [0, 0, 128]),
    ("Indigo", [75, 0, 130]),
    ("Purple", [128, 0, 128]),
    ("Medium Purple", [147, 112, 219]),
    ("Violet", [238, 130, 238]),
    ("Magenta", [255, 0, 255]),
    ("Hot Pink", [255, 105, 180]),
    ("Deep Pink", [255, 20, 147]),
    ("Pale Violet Red", [219, 112, 147]),
    ("Plum", [221, 160, 221]),
    ("Orchid", [218, 112, 214]),
    ("Lavender", [230, 230, 250]),
    ("Thistle", [216, 191, 216]),
    ("Khaki", [240, 230, 140]),
    ("Tan", [210, 180, 140]),
    ("Wheat", [245, 222, 179]),
    ("Burlywood", [222, 184, 135]),
    ("Chocolate", [210, 105, 30]),
    ("Saddle Brown", [139, 69, 19]),
    ("Sienna", [160, 82, 45]),
    ("Brown", [165, 42, 42]),
    ("Maroon", [128, 0, 0]),
    ("Light Gray", [211, 211, 211]),
    ("Silver", [192, 192, 192]),
    ("White", [255, 255, 255]),
]
GRADIENT_PALETTE = [
    ("Sunrise", [255, 40, 50], [255, 170, 60], [255, 255, 180]),
    ("Aurora", [0, 180, 255], [80, 255, 220], [220, 255, 255]),
    ("Berry Burst", [90, 0, 60], [210, 0, 140], [255, 140, 200]),
    ("Jungle Heat", [0, 140, 40], [255, 200, 40], [255, 40, 40]),
    ("Electric Blue", [0, 40, 255], [0, 220, 255], [180, 255, 255]),
    ("Neon Lime", [60, 255, 60], [190, 255, 0], [255, 255, 160]),
    ("Desert Glow", [255, 120, 60], [255, 200, 80], [255, 255, 220]),
    ("Coral Reef", [0, 210, 200], [255, 120, 70], [255, 230, 0]),
    ("Candy Pop", [255, 40, 140], [255, 160, 0], [255, 255, 120]),
    ("Ocean Depth", [0, 30, 80], [0, 130, 220], [120, 240, 255]),
    ("Galaxy", [30, 0, 90], [150, 0, 255], [255, 0, 180]),
    ("Mint Cream", [120, 255, 220], [80, 210, 255], [220, 255, 255]),
    ("Lava", [255, 0, 0], [255, 120, 0], [255, 255, 0]),
    ("Frostbite", [0, 60, 220], [140, 200, 255], [230, 250, 255]),
    ("Sunset Neon", [255, 80, 0], [255, 0, 120], [80, 0, 255]),
    ("Aurora Pink", [255, 160, 200], [255, 60, 180], [200, 0, 140]),
    ("Citrus", [255, 220, 0], [255, 140, 0], [255, 0, 120]),
    ("Lagoon", [0, 170, 220], [0, 230, 170], [130, 255, 220]),
    ("Berry Lime", [190, 40, 220], [0, 255, 120], [0, 200, 255]),
    ("Miami", [40, 250, 160], [10, 40, 90], [255, 0, 80]),
]
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle (heavy)",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain (heavy)",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Heavy rain showers",
    82: "Violent rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}
START_TIME = time.time()
ESP_DEFAULT_IP = os.getenv("ESP_IP", "10.42.0.13")
ESP2_DEFAULT_IP = os.getenv("ESP2_IP", "10.42.0.29")
ESP3_DEFAULT_IP = os.getenv("ESP3_IP", "10.42.0.173")
ESP3_CMD_TOPIC = os.getenv("ESP3_CMD_TOPIC", "esp32u/command")
ESP3_STATES_FILE = os.getenv("ESP3_STATE_FILE", os.path.join(os.path.dirname(__file__), "esp3_states.json"))

app = Flask(__name__)
# In-memory cache of last sent state (best effort for display)
STATE_CACHE = {seg: {"segment": seg, "pattern": "solid", "brightness": 180, "speed": 1.0, "color": [0, 180, 160], "wave_shape": "sine"} for seg in SEGMENTS}
for seg in STATE_CACHE:
    STATE_CACHE[seg]["wave_count"] = 5.0
    STATE_CACHE[seg]["mic_gain"] = 0.3
    STATE_CACHE[seg]["mic_floor"] = 0.02
    STATE_CACHE[seg]["mic_smooth"] = 0.3
    STATE_CACHE[seg]["mic_enabled"] = True
    STATE_CACHE[seg]["gradient_enabled"] = False
    STATE_CACHE[seg]["gradient_low"] = [0, 120, 255]
    STATE_CACHE[seg]["gradient_mid"] = [255, 255, 255]
    STATE_CACHE[seg]["gradient_high"] = [255, 0, 120]
    STATE_CACHE[seg]["mic_beat"] = False
ESP3_STATE: Dict[str, float] = {"brightness": 200, "white_balance": 4500, "last_pattern": "white", "target": "both"}
LAST_DEFAULT_APPLY = 0.0
LAST_ESP_UP = False
LAST_ESP3_UP = False
ESP3_OFF_LATCH = False


def publish(payload: Dict) -> None:
    client = mqtt.Client(client_id="led-web-ui")
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    try:
        client.publish(MQTT_CMD_TOPIC, json.dumps(payload), qos=0, retain=False)
    finally:
        client.loop_stop()
        client.disconnect()


def publish_esp3(payload: Dict) -> None:
    """Send a message to the ESP32U (camming lights) topic."""
    client = mqtt.Client(client_id="led-web-ui-esp3")
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    try:
        client.publish(ESP3_CMD_TOPIC, json.dumps(payload), qos=0, retain=False)
    finally:
        client.loop_stop()
        client.disconnect()


def color_temp_to_rgb(kelvin: float) -> List[int]:
    """Approximate color temperature (K) to RGB for white balance slider."""
    k = max(1500.0, min(9000.0, float(kelvin)))
    tmp = k / 100.0
    if tmp <= 66:
        red = 255
        green = 99.4708025861 * math.log(tmp) - 161.1195681661
        blue = 0 if tmp <= 19 else 138.5177312231 * math.log(tmp - 10) - 305.0447927307
    else:
        red = 329.698727446 * ((tmp - 60) ** -0.1332047592)
        green = 288.1221695283 * ((tmp - 60) ** -0.0755148492)
        blue = 255
    return [int(max(0, min(255, red))), int(max(0, min(255, green))), int(max(0, min(255, blue)))]


@dataclass
class Command:
    segment: str
    pattern: str
    brightness: float  # 0-255
    speed: float
    color: List[int]
    wave_shape: Optional[str] = None
    wave_count: float = 1.0
    mic_gain: Optional[float] = None
    mic_floor: Optional[float] = None
    mic_smooth: Optional[float] = None
    mic_enabled: Optional[bool] = None
    gradient_low: Optional[List[int]] = None
    gradient_mid: Optional[List[int]] = None
    gradient_high: Optional[List[int]] = None
    gradient_enabled: Optional[bool] = None
    mic_beat: Optional[bool] = None

    @classmethod
    def from_request(cls, data: Dict) -> "Command":
        return cls(
            segment=data.get("segment", "strip1"),
            pattern=data.get("pattern", "solid"),
            brightness=float(data.get("brightness", 255.0)),
            speed=float(data.get("speed", 1.0)),
            color=[int(x) for x in data.get("color", [0, 180, 160])][:3],
            wave_shape=data.get("wave_shape"),
            wave_count=float(data.get("wave_count", 1.0)),
            mic_gain=float(data["mic_gain"]) if "mic_gain" in data else None,
            mic_floor=float(data["mic_floor"]) if "mic_floor" in data else None,
            mic_smooth=float(data["mic_smooth"]) if "mic_smooth" in data else None,
            mic_enabled=bool(data["mic_enabled"]) if "mic_enabled" in data else None,
            gradient_low=[int(x) for x in data["gradient_low"]] if "gradient_low" in data else None,
            gradient_mid=[int(x) for x in data["gradient_mid"]] if "gradient_mid" in data else None,
            gradient_high=[int(x) for x in data["gradient_high"]] if "gradient_high" in data else None,
            gradient_enabled=bool(data["gradient_enabled"]) if "gradient_enabled" in data else None,
            mic_beat=bool(data["mic_beat"]) if "mic_beat" in data else None,
        )

    def to_payload(self) -> Dict:
        params: Dict = {"color": self.color}
        if self.wave_shape:
            params["wave_shape"] = self.wave_shape
        if self.wave_count is not None:
            params["wave_count"] = self.wave_count
        if self.mic_gain is not None:
            params["mic_gain"] = self.mic_gain
        if self.mic_floor is not None:
            params["mic_floor"] = self.mic_floor
        if self.mic_smooth is not None:
            params["mic_smooth"] = self.mic_smooth
        if self.mic_enabled is not None:
            params["mic_enabled"] = self.mic_enabled
        if self.gradient_low is not None:
            params["gradient_low"] = self.gradient_low
        if self.gradient_mid is not None:
            params["gradient_mid"] = self.gradient_mid
        if self.gradient_high is not None:
            params["gradient_high"] = self.gradient_high
        if self.gradient_enabled is not None:
            params["gradient_enabled"] = self.gradient_enabled
        if self.mic_beat is not None:
            params["mic_beat"] = self.mic_beat
        return {
            "cmd": "set",
            "segment": self.segment,
            "pattern": self.pattern,
            "brightness": self.brightness,
            "speed": self.speed,
            "params": params,
        }


@app.route("/")
def index():
    return render_template_string(
        HTML,
        segments=SEGMENTS,
        patterns=PATTERNS,
        mqtt_host=MQTT_HOST,
        mqtt_topic=MQTT_CMD_TOPIC,
        esp_default_ip=ESP_DEFAULT_IP,
        esp2_default_ip=ESP2_DEFAULT_IP,
        esp3_default_ip=ESP3_DEFAULT_IP,
        segment_labels=SEGMENT_LABELS,
        colors=COLOR_PALETTE,
        gradients=GRADIENT_PALETTE,
    )


@app.route("/api/set", methods=["POST"])
def api_set():
    data = request.get_json(force=True)
    cmd = Command.from_request(data)
    publish(cmd.to_payload())
    STATE_CACHE[cmd.segment] = {
        "segment": cmd.segment,
        "pattern": cmd.pattern,
        "brightness": cmd.brightness,
        "speed": cmd.speed,
        "color": cmd.color,
        "wave_shape": cmd.wave_shape or "",
        "wave_count": cmd.wave_count,
        "mic_gain": cmd.mic_gain if cmd.mic_gain is not None else STATE_CACHE[cmd.segment].get("mic_gain", 4.0),
        "mic_floor": cmd.mic_floor if cmd.mic_floor is not None else STATE_CACHE[cmd.segment].get("mic_floor", 0.02),
        "mic_smooth": cmd.mic_smooth if cmd.mic_smooth is not None else STATE_CACHE[cmd.segment].get("mic_smooth", 0.8),
        "mic_enabled": cmd.mic_enabled if cmd.mic_enabled is not None else STATE_CACHE[cmd.segment].get("mic_enabled", True),
        "gradient_enabled": cmd.gradient_enabled if cmd.gradient_enabled is not None else STATE_CACHE[cmd.segment].get("gradient_enabled", False),
        "gradient_low": cmd.gradient_low if cmd.gradient_low is not None else STATE_CACHE[cmd.segment].get("gradient_low", [0, 120, 255]),
        "gradient_mid": cmd.gradient_mid if cmd.gradient_mid is not None else STATE_CACHE[cmd.segment].get("gradient_mid", [255, 255, 255]),
        "gradient_high": cmd.gradient_high if cmd.gradient_high is not None else STATE_CACHE[cmd.segment].get("gradient_high", [255, 0, 120]),
    }
    return jsonify({"ok": True})


@app.route("/api/ping", methods=["POST"])
def api_ping():
    seg = request.get_json(force=True).get("segment", "strip1")
    publish({"cmd": "ping", "segment": seg})
    return jsonify({"ok": True})


@app.route("/api/status")
def api_status():
    uptime = time.time() - START_TIME
    return jsonify(
        {
            "service": "running",
            "uptime_seconds": round(uptime, 1),
            "mqtt_host": MQTT_HOST,
            "mqtt_topic": MQTT_CMD_TOPIC,
            "esp_default_ip": ESP_DEFAULT_IP,
            "esp3_default_ip": ESP3_DEFAULT_IP,
        }
    )


@app.route("/api/weather")
def api_weather():
    """Fetch weather for given lat/lon; falls back to cached/manual when offline."""
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    label = request.args.get("label", "Your location")
    cache_only = str(request.args.get("cache_only", "")).lower() in ("1", "true", "yes")
    cache = read_weather_cache()

    if cache_only or lat is None or lon is None:
        if cache:
            resp = dict(cache)
            resp["ok"] = True
            resp["source"] = "cache"
            return jsonify(resp)
        return jsonify({"ok": False, "error": "missing_location_and_cache"})

    try:
        snap = fetch_weather(lat, lon, label or "Your location")
        snap["ok"] = True
        snap["source"] = snap.get("source", "open-meteo")
        return jsonify(snap)
    except Exception as exc:
        if cache:
            resp = dict(cache)
            resp["ok"] = True
            resp["source"] = "cache"
            resp["error"] = str(exc)
            return jsonify(resp)
        return jsonify({"ok": False, "error": "unavailable"})


@app.route("/api/weather/manual", methods=["POST"])
def api_weather_manual():
    """Allow manual/offline weather entry; also persists to cache."""
    data = request.get_json(force=True) or {}

    def _num(val):
        try:
            return float(val)
        except Exception:
            return None

    payload = {
        "location": (data.get("location") or data.get("label") or "Manual entry"),
        "lat": _num(data.get("lat")),
        "lon": _num(data.get("lon")),
        "temp_f": _num(data.get("temp_f") or data.get("temp")),
        "humidity": _num(data.get("humidity")),
        "wind_mph": _num(data.get("wind_mph") or data.get("wind")),
        "condition": data.get("condition") or "Manual entry",
        "updated": datetime.utcnow().isoformat() + "Z",
        "source": "manual",
    }
    write_weather_cache(payload)
    return jsonify({"ok": True, **payload})


def load_esp3_states() -> (Dict[str, Dict], Optional[str]):
    if not os.path.exists(ESP3_STATES_FILE):
        return {}, None
    try:
        with open(ESP3_STATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("states", {}), data.get("default")
    except Exception:
        pass
    return {}, None


def write_esp3_states(states: Dict[str, Dict], default_name: Optional[str] = None) -> None:
    payload = {"states": states}
    if default_name and default_name in states:
        payload["default"] = default_name
    try:
        with open(ESP3_STATES_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def _apply_esp3_snapshot(data: Dict) -> Dict:
    """Apply a camming snapshot dict."""
    pattern = data.get("pattern", ESP3_STATE.get("last_pattern", "white"))
    if pattern not in CAMMING_PATTERNS:
        pattern = "white"
    brightness = data.get("brightness", ESP3_STATE.get("brightness", 200))
    white_balance = data.get("white_balance", ESP3_STATE.get("white_balance", 4500))
    target = data.get("target", ESP3_STATE.get("target", "both"))
    payload = {
        "cmd": "set",
        "pattern": pattern,
        "brightness": brightness,
        "white_balance": white_balance,
        "target": target,
        "strips": [{"pin": 33, "length": 300}, {"pin": 32, "length": 300}],
    }
    if pattern == "white":
        payload["color"] = color_temp_to_rgb(white_balance)
    publish_esp3(payload)
    ESP3_STATE.update(
        {
            "brightness": float(brightness),
            "white_balance": float(white_balance),
            "last_pattern": pattern,
            "target": target,
        }
    )
    return ESP3_STATE


def apply_default_esp3() -> bool:
    if ESP3_OFF_LATCH:
        return False
    states, default_name = load_esp3_states()
    if not default_name or default_name not in states:
        return False
    _apply_esp3_snapshot(states[default_name])
    return True


@app.route("/api/esp3/state")
def api_esp3_state():
    return jsonify({"ok": True, "state": ESP3_STATE, "ip": ESP3_DEFAULT_IP})


@app.route("/api/esp3/states", methods=["GET"])
def api_esp3_states():
    states, default_name = load_esp3_states()
    payload = [{"name": k, "data": v} for k, v in sorted(states.items())]
    return jsonify({"states": payload, "default": default_name})


@app.route("/api/esp3/state/save", methods=["POST"])
def api_esp3_state_save():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Name required"}), 400
    states, default_name = load_esp3_states()
    snapshot = {
        "pattern": ESP3_STATE.get("last_pattern", "white"),
        "brightness": ESP3_STATE.get("brightness", 200),
        "white_balance": ESP3_STATE.get("white_balance", 4500),
        "target": ESP3_STATE.get("target", "both"),
    }
    states[name] = snapshot
    write_esp3_states(states, default_name)
    return jsonify({"ok": True, "state": {"name": name, "data": snapshot}})


@app.route("/api/esp3/state/apply", methods=["POST"])
def api_esp3_state_apply():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()
    states, default_name = load_esp3_states()
    if not name or name not in states:
        return jsonify({"ok": False, "error": "State not found"}), 404
    data = states[name]
    new_state = _apply_esp3_snapshot(data)
    return jsonify({"ok": True, "state": {"name": name, "data": data}, "applied": new_state})


@app.route("/api/esp3/state/default", methods=["POST"])
def api_esp3_state_default():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()
    states, _ = load_esp3_states()
    if not name or name not in states:
        return jsonify({"ok": False, "error": "State not found"}), 404
    write_esp3_states(states, name)
    _apply_esp3_snapshot(states[name])
    return jsonify({"ok": True, "default": name})


@app.route("/api/esp3/state/delete", methods=["POST"])
def api_esp3_state_delete():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()
    states, default_name = load_esp3_states()
    if not name or name not in states:
        return jsonify({"ok": False, "error": "State not found"}), 404
    states.pop(name, None)
    if default_name == name:
        default_name = None
    write_esp3_states(states, default_name)
    return jsonify({"ok": True, "default": default_name})


@app.route("/api/esp3/set", methods=["POST"])
def api_esp3_set():
    global ESP3_OFF_LATCH
    body = request.get_json(force=True) or {}
    pattern = body.get("pattern", "white")
    brightness = body.get("brightness", ESP3_STATE.get("brightness", 200))
    white_balance = body.get("white_balance", ESP3_STATE.get("white_balance", 4500))
    target = body.get("target", "both")
    if pattern not in CAMMING_PATTERNS:
        pattern = "white"
    payload: Dict = {
        "cmd": "set",
        "pattern": pattern,
        "target": target,
        "strips": [{"pin": 33, "length": 300}, {"pin": 32, "length": 300}],
    }
    brightness_val = None
    if brightness is not None:
        brightness_val = float(brightness)
        payload["brightness"] = brightness_val
        ESP3_OFF_LATCH = brightness_val <= 0
    else:
        brightness_val = ESP3_STATE.get("brightness")
    wb = float(white_balance) if white_balance is not None else 4500.0
    payload["white_balance"] = wb
    if pattern == "white":
        payload["color"] = color_temp_to_rgb(wb)
    publish_esp3(payload)
    ESP3_STATE.update(
        {
            "brightness": brightness_val if brightness_val is not None else ESP3_STATE.get("brightness"),
            "white_balance": wb,
            "last_pattern": payload.get("pattern", pattern),
            "target": target,
        }
    )
    return jsonify({"ok": True, "state": ESP3_STATE})

@app.route("/api/pi-temp")
def api_pi_temp():
    temp = read_pi_temp()
    return jsonify({"temp_c": temp, "ok": temp is not None})


@app.route("/api/states", methods=["GET"])
def api_states():
    states, default_name = load_states()
    payload = [{"name": k, "data": v} for k, v in sorted(states.items())]
    return jsonify({"states": payload, "default": default_name})


@app.route("/api/state/save", methods=["POST"])
def api_state_save():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Name required"}), 400
    states, default_name = load_states()
    # Snapshot current in-memory state for every segment.
    snapshot = {"segments": {}}
    for seg, data in STATE_CACHE.items():
        snapshot["segments"][seg] = dict(data)
    states[name] = snapshot
    write_states(states, default_name)
    return jsonify({"ok": True, "state": {"name": name, "data": snapshot}})


@app.route("/api/state/apply", methods=["POST"])
def api_state_apply():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()
    states, default_name = load_states()
    if not name or name not in states:
        return jsonify({"ok": False, "error": "State not found"}), 404
    data = states[name]
    _apply_segments_snapshot(data)
    return jsonify({"ok": True, "state": {"name": name, "data": data}})


@app.route("/api/esp-status")
def api_esp_status():
    # Try to reach ESP32 on the LAN; default from ESP_IP env or last known IP.
    from subprocess import run, DEVNULL

    target = request.args.get("ip") or ESP_DEFAULT_IP or guess_esp_ip()
    try:
        res = run(["ping", "-c", "1", "-W", "1", target], stdout=DEVNULL, stderr=DEVNULL)
        ok = res.returncode == 0
    except Exception:
        ok = False
    return jsonify({"ip": target, "reachable": ok})


def check_wlan():
    try:
        from subprocess import check_output

        out = check_output(["ip", "-4", "addr", "show", "wlan0"], text=True)
        lines = [ln.strip() for ln in out.splitlines()]
        ip = None
        up = "state UP" in out or "LOWER_UP" in out
        for ln in lines:
            if ln.startswith("inet "):
                ip = ln.split()[1]
                break
        return {"up": up, "ip": ip}
    except Exception:
        return {"up": False, "ip": None}


def check_mqtt():
    import socket

    try:
        with socket.create_connection((MQTT_HOST, MQTT_PORT), timeout=1.0):
            return True
    except Exception:
        return False


def ping_ip(target: str) -> bool:
    from subprocess import run, DEVNULL

    try:
        res = run(["ping", "-c", "1", "-W", "1", target], stdout=DEVNULL, stderr=DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def restart_mosquitto():
    from subprocess import run, DEVNULL

    try:
        res = run(["sudo", "systemctl", "restart", "mosquitto"], stdout=DEVNULL, stderr=DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def reset_esp_serial(port: str = "/dev/ttyACM0"):
    import os
    from subprocess import run, DEVNULL

    if not os.path.exists(port):
        return False
    # Try esptool reset via the tool shipped with Arduino core.
    candidates = [
        "/home/sophie/.arduino15/packages/esp32/tools/esptool_py/5.1.0/esptool.py",
        "esptool.py",
    ]
    for tool in candidates:
        try:
            res = run(
                [tool, "--chip", "esp32s3", "--port", port, "--before", "default_reset", "--after", "hard_reset", "chip_id"],
                stdout=DEVNULL,
                stderr=DEVNULL,
            )
            if res.returncode == 0:
                return True
        except Exception:
            continue
    return False


def read_pi_temp() -> Optional[float]:
    """Return Pi CPU temperature in Celsius if available."""
    # Primary path exposed by Raspberry Pi OS kernels.
    path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            return round(float(raw) / 1000.0, 1)
    except Exception:
        pass
    # Fallback to vcgencmd if installed.
    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True).strip()
        if out.startswith("temp=") and out.endswith("'C"):
            return round(float(out.split("=")[1].split("'")[0]), 1)
    except Exception:
        pass
    return None


def guess_esp_ip() -> Optional[str]:
    """Try to guess ESP IP from dnsmasq leases if available."""
    lease_file = "/var/lib/misc/dnsmasq.leases"
    nm_lease_file = "/var/lib/NetworkManager/dnsmasq-wlan1.leases"
    last_ip = None
    try:
        with open(lease_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    ip = parts[2]
                    last_ip = ip
                    host = parts[3] if len(parts) >= 4 else ""
                    if "esp32" in host.lower():
                        return ip
    except Exception:
        pass
    try:
        with open(nm_lease_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    ip = parts[2]
                    last_ip = ip
                    host = parts[3] if len(parts) >= 4 else ""
                    if "esp" in host.lower():
                        return ip
    except Exception:
        pass
    return last_ip


def read_weather_cache() -> Optional[Dict]:
    """Load the last known weather snapshot from disk."""
    if not os.path.exists(WEATHER_CACHE_FILE):
        return None
    try:
        with open(WEATHER_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        return None
    return None


def write_weather_cache(data: Dict) -> None:
    """Persist weather snapshot; best-effort (ignore errors)."""
    try:
        with open(WEATHER_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def fetch_weather(lat: float, lon: float, label: str) -> Dict:
    """Fetch current weather from open-meteo for the given coords."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
    )
    resp = requests.get(url, timeout=8)
    resp.raise_for_status()
    data = resp.json() or {}
    current = data.get("current") or {}

    def _safe_round(val, default=None):
        try:
            return round(float(val))
        except Exception:
            return default

    code_val = current.get("weather_code")
    try:
        code_int = int(code_val)
    except Exception:
        code_int = None
    condition = WEATHER_CODES.get(code_int, "Weather")
    snapshot = {
        "location": label or "Your location",
        "lat": lat,
        "lon": lon,
        "temp_f": _safe_round(current.get("temperature_2m")),
        "humidity": _safe_round(current.get("relative_humidity_2m")),
        "wind_mph": _safe_round(current.get("wind_speed_10m")),
        "condition": condition,
        "code": code_int,
        "updated": datetime.utcnow().isoformat() + "Z",
        "source": "open-meteo",
    }
    write_weather_cache(snapshot)
    return snapshot


def _apply_segments_snapshot(data: Dict) -> None:
    """Apply a snapshot dict containing 'segments': {seg: {..}} or legacy single-segment dict."""
    global LAST_DEFAULT_APPLY
    segments = {}
    if isinstance(data, dict) and "segments" in data and isinstance(data["segments"], dict):
        segments = data["segments"]
    elif isinstance(data, dict):
        seg_name = data.get("segment", "strip1")
        segments = {seg_name: data}
    for seg_name, seg_data in segments.items():
        payload = dict(seg_data)
        payload["segment"] = seg_name
        cmd = Command.from_request(payload)
        publish(cmd.to_payload())
        STATE_CACHE[seg_name] = {
            "segment": seg_name,
            "pattern": cmd.pattern,
            "brightness": cmd.brightness,
            "speed": cmd.speed,
            "color": cmd.color,
            "wave_shape": cmd.wave_shape,
            "wave_count": cmd.wave_count,
            "mic_gain": cmd.mic_gain if cmd.mic_gain is not None else STATE_CACHE.get(seg_name, {}).get("mic_gain"),
            "mic_floor": cmd.mic_floor if cmd.mic_floor is not None else STATE_CACHE.get(seg_name, {}).get("mic_floor"),
            "mic_smooth": cmd.mic_smooth if cmd.mic_smooth is not None else STATE_CACHE.get(seg_name, {}).get("mic_smooth"),
            "mic_enabled": cmd.mic_enabled if cmd.mic_enabled is not None else STATE_CACHE.get(seg_name, {}).get("mic_enabled"),
            "gradient_enabled": cmd.gradient_enabled if cmd.gradient_enabled is not None else STATE_CACHE.get(seg_name, {}).get("gradient_enabled"),
            "gradient_low": cmd.gradient_low if cmd.gradient_low is not None else STATE_CACHE.get(seg_name, {}).get("gradient_low"),
            "gradient_mid": cmd.gradient_mid if cmd.gradient_mid is not None else STATE_CACHE.get(seg_name, {}).get("gradient_mid"),
            "gradient_high": cmd.gradient_high if cmd.gradient_high is not None else STATE_CACHE.get(seg_name, {}).get("gradient_high"),
        }
    LAST_DEFAULT_APPLY = time.time()


def apply_default_state() -> bool:
    """Apply the currently saved default state, if any."""
    states, default_name = load_states()
    if not default_name or default_name not in states:
        return False
    _apply_segments_snapshot(states[default_name])
    return True


def start_default_watcher():
    """Background thread: when ESP comes online, push the default preset."""
    import threading

    def loop():
        global LAST_ESP_UP
        while True:
            reachable = ping_ip(ESP_DEFAULT_IP)
            if reachable and not LAST_ESP_UP:
                apply_default_state()
            LAST_ESP_UP = reachable
            time.sleep(5)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def start_esp3_default_watcher():
    """Background thread: when camming ESP comes online, push its default preset."""
    import threading

    def loop():
        global LAST_ESP3_UP
        while True:
            reachable = ping_ip(ESP3_DEFAULT_IP)
            if reachable and not LAST_ESP3_UP:
                apply_default_esp3()
            LAST_ESP3_UP = reachable
            time.sleep(5)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def load_states() -> (Dict[str, Dict], Optional[str]):
    """Load saved LED states from disk.
    Returns (states_dict, default_name). Supports both legacy dict-only format and new wrapped format.
    Ensures each entry is normalized to {"segments": {...}}.
    """
    if not os.path.exists(STATES_FILE):
        return {}, None
    raw_states = {}
    default_name = None
    try:
        with open(STATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                if "states" in data and isinstance(data["states"], dict):
                    raw_states = data["states"]
                    default_name = data.get("default")
                else:
                    raw_states = data
    except Exception:
        return {}, None

    normalized = {}
    for name, val in raw_states.items():
        if isinstance(val, dict) and "segments" in val and isinstance(val["segments"], dict):
            normalized[name] = val
            continue
        # Legacy: single-segment dict
        if isinstance(val, dict):
            seg_name = val.get("segment", "strip1")
            normalized[name] = {"segments": {seg_name: val}}
    return normalized, default_name


def write_states(states: Dict[str, Dict], default_name: Optional[str] = None) -> None:
    """Persist states to disk; best-effort."""
    payload = {"states": states}
    if default_name and default_name in states:
        payload["default"] = default_name
    try:
        with open(STATES_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


@app.route("/api/troubleshoot")
def api_troubleshoot():
    target = request.args.get("ip") or guess_esp_ip() or ESP_DEFAULT_IP
    from subprocess import run, DEVNULL

    mosq_restarted = False  # skip restart to avoid privilege issues
    wlan = check_wlan()
    esp_ok = ping_ip(target)
    mqtt_ok = check_mqtt()
    esp_reset = reset_esp_serial()

    suggestions = []
    if not mqtt_ok:
        suggestions.append("Ensure mosquitto is running on the Pi (systemctl restart mosquitto) and port 1883 allows LAN clients.")
    if not esp_ok:
        suggestions.append("Power-cycle ESP32 and verify it joins SSID HotMess (pass: transgender).")

    return jsonify(
        {
            "esp_ip": target,
            "esp_reachable": esp_ok,
            "mqtt_reachable": mqtt_ok,
            "mosquitto_restarted": mosq_restarted,
            "esp_reset_attempted": esp_reset,
            "wlan": wlan,
            "suggestions": suggestions,
            "state": list(STATE_CACHE.values()),
        }
    )


@app.route("/api/state")
def api_state():
    return jsonify({"state": list(STATE_CACHE.values())})


@app.route("/api/state/default", methods=["POST"])
def api_state_default():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()
    states, _ = load_states()
    if not name or name not in states:
        return jsonify({"ok": False, "error": "State not found"}), 404
    # Save default and apply it immediately so lights match the choice.
    write_states(states, name)
    _apply_segments_snapshot(states[name])
    return jsonify({"ok": True, "default": name})


@app.route("/api/state/delete", methods=["POST"])
def api_state_delete():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()
    states, default_name = load_states()
    if not name or name not in states:
        return jsonify({"ok": False, "error": "State not found"}), 404
    states.pop(name, None)
    if default_name == name:
        default_name = None
    write_states(states, default_name)
    return jsonify({"ok": True, "default": default_name})


@app.route("/api/state/apply-default", methods=["POST"])
def api_state_apply_default():
    ok = apply_default_state()
    return jsonify({"ok": ok})


@app.route("/api/close-chromium", methods=["POST"])
def api_close_chromium():
    """Best-effort kill Chromium so the kiosk window closes."""
    errors = []
    killed = False
    for pattern in ("chromium-browser", "chromium"):
        try:
            res = subprocess.run(["pkill", "-f", pattern], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                killed = True
        except Exception as exc:
            errors.append(str(exc))
    ok = not errors
    return jsonify({"ok": ok, "killed": killed, "errors": errors})


@app.route("/api/set-all", methods=["POST"])
def api_set_all():
    data = request.get_json(force=True)
    brightness = data.get("brightness")
    pattern = data.get("pattern")
    color = data.get("color")
    wave_shape = data.get("wave_shape")
    speed = data.get("speed")
    wave_count = data.get("wave_count")
    mic_gain = data.get("mic_gain")
    mic_floor = data.get("mic_floor")
    mic_smooth = data.get("mic_smooth")
    mic_enabled = data.get("mic_enabled")
    mic_beat = data.get("mic_beat")
    for seg in SEGMENTS:
        payload = {"cmd": "set", "segment": seg}
        if brightness is not None:
            payload["brightness"] = float(brightness)
        if pattern:
            payload["pattern"] = pattern
        if speed is not None:
            payload["speed"] = float(speed)
        params = {}
        if color:
            params["color"] = [int(x) for x in color[:3]]
        if wave_shape:
            params["wave_shape"] = wave_shape
        if wave_count is not None:
            params["wave_count"] = float(wave_count)
        if mic_gain is not None:
            params["mic_gain"] = float(mic_gain)
        if mic_floor is not None:
            params["mic_floor"] = float(mic_floor)
        if mic_smooth is not None:
            params["mic_smooth"] = float(mic_smooth)
        if mic_enabled is not None:
            params["mic_enabled"] = bool(mic_enabled)
        if mic_beat is not None:
            params["mic_beat"] = bool(mic_beat)
        if params:
            payload["params"] = params
        publish(payload)
        cached = STATE_CACHE.get(seg, {"segment": seg})
        if brightness is not None:
            cached["brightness"] = float(brightness)
        if pattern:
            cached["pattern"] = pattern
        if speed is not None:
            cached["speed"] = float(speed)
        if color:
            cached["color"] = [int(x) for x in color[:3]]
        if wave_shape:
            cached["wave_shape"] = wave_shape
        if wave_count is not None:
            cached["wave_count"] = float(wave_count)
        if mic_gain is not None:
            cached["mic_gain"] = float(mic_gain)
        if mic_floor is not None:
            cached["mic_floor"] = float(mic_floor)
        if mic_smooth is not None:
            cached["mic_smooth"] = float(mic_smooth)
        if mic_enabled is not None:
            cached["mic_enabled"] = bool(mic_enabled)
        if mic_beat is not None:
            cached["mic_beat"] = bool(mic_beat)
        STATE_CACHE[seg] = cached
    return jsonify({"ok": True, "state": list(STATE_CACHE.values())})


@app.route("/weather")
def weather_page():
    return render_template_string(
        WEATHER_HTML,
        last_weather=read_weather_cache() or {},
        quickmenu_url="/quickmenu",
    )


@app.route("/quickmenu")
def quickmenu():
    return render_template_string(
        QUICKMENU_HTML,
        patterns=PATTERNS,
        esp_default_ip=ESP_DEFAULT_IP,
        esp2_default_ip=ESP2_DEFAULT_IP,
        esp3_default_ip=ESP3_DEFAULT_IP,
    )



QUICKMENU_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <title>LED Quick Menu</title>
  <style>
    :root {
      --bg: #060b16;
      --card: #0f1629;
      --accent: #5eead4;
      --accent-2: #fbbf24;
      --text: #e8edf7;
      --muted: #9fb0d0;
      --danger: #ef4444;
      --shadow: 0 10px 30px rgba(0,0,0,0.35);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(120% 120% at 20% 20%, #0f1b2e 0%, #050912 60%, #04060c 100%);
      font-family: "Inter", "Segoe UI", system-ui, sans-serif;
      color: var(--text);
      min-height: 100vh;
      scrollbar-width: none;
      -ms-overflow-style: none;
    }
    body::-webkit-scrollbar { display: none; }
    .wrap { width: min(900px, 96vw); margin: 0 auto; padding: 16px 16px 22px; }
    .card {
      background: var(--card);
      border: 1px solid #1d2740;
      border-radius: 16px;
      padding: 14px;
      margin-top: 12px;
      box-shadow: var(--shadow);
    }
    .label { font-size: 14px; color: var(--muted); margin-bottom: 6px; letter-spacing: 0.2px; }
    .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
    input[type=range] { width: 100%; accent-color: var(--accent); }
    .pill {
      background: rgba(255,255,255,0.08);
      border: 1px solid #263654;
      border-radius: 999px;
      padding: 8px 12px;
      font-weight: 700;
      min-width: 58px;
      text-align:center;
    }
    button, .ghost-link {
      appearance: none;
      border: none;
      border-radius: 12px;
      padding: 12px 14px;
      font-size: 17px;
      font-weight: 700;
      color: #0c111a;
      background: linear-gradient(135deg, var(--accent), #3db9a5);
      box-shadow: 0 8px 24px rgba(94, 234, 212, 0.25);
      cursor: pointer;
      min-width: 96px;
      text-decoration: none;
      text-align: center;
    }
    button:active, .ghost-link:active { transform: translateY(1px); }
    .ghost-link { display:inline-block; color: var(--text); background: rgba(255,255,255,0.08); box-shadow: none; border: 1px solid #263654; }
    .danger { background: linear-gradient(135deg, #f87171, #ef4444); box-shadow: 0 8px 24px rgba(239, 68, 68, 0.25); color: #1b0b0b; }
    .pattern-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
    .chip { width: 100%; }
    .status {
      margin-top: 14px;
      color: var(--muted);
      font-size: 14px;
      text-align: center;
    }
    .badges { display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin-top:10px; }
    .badge { display:inline-flex; align-items:center; gap:8px; padding:8px 12px; border-radius:12px; background: rgba(255,255,255,0.06); border:1px solid #263654; }
    .dot { width:10px; height:10px; border-radius:50%; background:#f97316; box-shadow:0 0 10px rgba(249,115,22,0.7); }
    @media (max-width: 700px) {
      button, .ghost-link { width: 100%; }
      .row { flex-direction: column; align-items: stretch; }
      .pattern-grid { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="label">Global brightness</div>
      <div class="row">
        <input id="brightness" type="range" min="0" max="255" value="180" oninput="updateBrightness(this.value)">
        <div class="pill" id="bval">180</div>
      </div>
      <div class="row" style="margin-top:8px;">
        <button onclick="lightsOn()">On</button>
        <button class="danger" onclick="lightsOff()">Off</button>
      </div>
    </div>
    <div class="card">
      <div class="label">Pattern</div>
      <div id="pattern-grid" class="pattern-grid"></div>
    </div>
    <div class="card">
      <div class="label">Camming lights</div>
      <div class="row">
        <input id="qm-cam-brightness" type="range" min="0" max="255" value="200" oninput="updateQmCamBrightness(this.value)">
        <div class="pill" id="qm-cam-bval">200</div>
      </div>
      <div class="row" style="margin-top:10px;">
        <button onclick="qmCamWhite()">White</button>
        <button class="ghost-link" onclick="qmCamRainbow()">Rainbow</button>
        <button class="ghost-link" onclick="qmCamHills()">Rainbow hills</button>
        <button class="danger" onclick="qmCamOff()">Off</button>
      </div>
    </div>
    <div class="card">
      <div class="label">Shortcuts</div>
      <div class="row">
        <a class="ghost-link" href="/">Open full UI</a>
        <a class="ghost-link" href="/weather">Weather</a>
        <button class="ghost-link" onclick="window.location.reload()">Reload</button>
      </div>
    </div>
    <div id="status" class="status">Ready.</div>
    <div class="badges">
      <div class="badge" id="esp1-badge"><span class="dot" id="esp1-dot"></span><span id="esp1-text">ESP1: …</span></div>
      <div class="badge" id="esp2-badge"><span class="dot" id="esp2-dot"></span><span id="esp2-text">ESP2: …</span></div>
      <div class="badge" id="esp3-badge"><span class="dot" id="esp3-dot"></span><span id="esp3-text">ESP3: …</span></div>
    </div>
    <div class="card" style="margin-top:14px; text-align:center;">
      <button class="danger" style="width:100%;" onclick="closeChromium()">Close Chromium</button>
      <div class="label" style="margin-top:8px; text-align:center;">Close the kiosk Chromium window on the Pi.</div>
    </div>
  </div>
  <script>
const patterns = {{ patterns|tojson }};
const espIp = "{{ esp_default_ip }}";
const esp2Ip = "{{ esp2_default_ip }}";
const esp3Ip = "{{ esp3_default_ip }}";
const statusEl = document.getElementById('status');
const brightnessEl = document.getElementById('brightness');
const bval = document.getElementById('bval');
const qmCamB = document.getElementById('qm-cam-brightness');
const qmCamBVal = document.getElementById('qm-cam-bval');
let qmCamLastPattern = 'white';
let qmCamSendTimer = null;
let lastBrightness = parseFloat(brightnessEl.value || '180');
let brightnessTimer = null;

    function setStatus(msg) { statusEl.textContent = msg; }

    async function postJson(url, body) {
      return fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body || {})});
    }

    function updateBrightness(val) {
      const num = parseFloat(val);
      bval.textContent = val;
      setStatus(`Brightness ${val}`);
      if (num > 0) lastBrightness = num;
      if (brightnessTimer) clearTimeout(brightnessTimer);
      brightnessTimer = setTimeout(() => {
        postJson('/api/set-all', {brightness: num}).catch(() => {});
      }, 80);
    }

    function updateQmCamBrightness(val) {
      qmCamBVal.textContent = val;
      if (qmCamSendTimer) clearTimeout(qmCamSendTimer);
      qmCamSendTimer = setTimeout(() => {
        qmCamSend({pattern: qmCamLastPattern || 'white', brightness: parseFloat(qmCamB.value || '200'), target:'both'});
      }, 120);
    }

    async function qmCamSend(body) {
      await postJson('/api/esp3/set', body);
    }
    async function qmCamWhite() {
      qmCamLastPattern = 'white';
      await qmCamSend({pattern: 'white', brightness: parseFloat(qmCamB.value || '200'), target:'both'});
      setStatus('Camming: white');
    }
    async function qmCamRainbow() {
      qmCamLastPattern = 'rainbow';
      await qmCamSend({pattern: 'rainbow', brightness: parseFloat(qmCamB.value || '200'), target:'both'});
      setStatus('Camming: rainbow');
    }
    async function qmCamHills() {
      qmCamLastPattern = 'rainbow_hills';
      await qmCamSend({pattern: 'rainbow_hills', brightness: parseFloat(qmCamB.value || '200'), target:'both'});
      setStatus('Camming: rainbow hills');
    }
    async function qmCamOff() {
      qmCamSendTimer && clearTimeout(qmCamSendTimer);
      qmCamB.value = 0;
      qmCamBVal.textContent = '0';
      await qmCamSend({pattern: qmCamLastPattern || 'white', brightness: 0, target:'both'});
      setStatus('Camming: off');
    }

    async function setPattern(name) {
      setStatus(`Pattern: ${name}`);
      await postJson('/api/set-all', {pattern: name});
    }

    async function lightsOn() {
      setStatus('Lights on');
      let val = lastBrightness > 0 ? lastBrightness : 180;
      // Try to apply saved default; fall back to a gentle brightness.
      try {
        const res = await postJson('/api/state/apply-default', {});
        const data = await res.json();
        if (!data.ok) {
          await postJson('/api/set-all', {brightness: val});
        }
      } catch (e) {
        await postJson('/api/set-all', {brightness: val});
      }
      // Bring camming lights up as well.
      await qmCamSend({pattern: qmCamLastPattern || 'white', brightness: parseFloat(qmCamB.value || '200'), target:'both'});
      brightnessEl.value = val;
      bval.textContent = val;
    }

    async function lightsOff() {
      const current = parseFloat(brightnessEl.value || '0');
      if (current > 0) lastBrightness = current;
      setStatus('Lights off');
      brightnessEl.value = 0;
      bval.textContent = '0';
      await postJson('/api/set-all', {brightness: 0});
      await qmCamSend({pattern: qmCamLastPattern || 'white', brightness: 0, target:'both'});
    }

    async function closeChromium() {
      setStatus('Closing Chromium...');
      try {
        const res = await fetch('/api/close-chromium', {method:'POST'});
        const data = await res.json();
        if (data && data.killed) {
          setStatus('Chromium close requested.');
        } else {
          setStatus('No Chromium processes were running.');
        }
      } catch (e) {
        setStatus('Close Chromium failed.');
      }
    }

    function renderPatterns() {
      const grid = document.getElementById('pattern-grid');
      patterns.forEach((name) => {
        const btn = document.createElement('button');
        btn.textContent = name;
        btn.className = 'chip';
        btn.onclick = () => setPattern(name);
        grid.appendChild(btn);
      });
    }

    async function syncInitial() {
      try {
        const res = await fetch('/api/state');
        const data = await res.json();
        if (data && data.state && data.state.length) {
          const first = data.state[0];
          if (first && typeof first.brightness !== 'undefined') {
            brightnessEl.value = first.brightness;
            bval.textContent = first.brightness;
          }
        }
      } catch (e) {
        // ignore
      }
    }

    renderPatterns();
    syncInitial();
    (async () => {
      try {
        const res = await fetch('/api/esp3/state');
        const data = await res.json();
        if (data && data.state && typeof data.state.brightness !== 'undefined') {
          qmCamB.value = data.state.brightness;
          qmCamBVal.textContent = data.state.brightness;
          if (data.state.last_pattern) qmCamLastPattern = data.state.last_pattern;
        }
      } catch (e) {
        // ignore
      }
    })();

    async function refreshEspBadge(ip, dotEl, textEl, label) {
      if (!dotEl || !textEl) return;
      try {
        const res = await fetch(`/api/esp-status?ip=${encodeURIComponent(ip)}`);
        const data = await res.json();
        if (data.reachable) {
          dotEl.style.background = '#22c55e';
          dotEl.style.boxShadow = '0 0 10px rgba(34,197,94,0.7)';
          textEl.textContent = `${label} ${data.ip}: online`;
        } else {
          dotEl.style.background = '#ef4444';
          dotEl.style.boxShadow = '0 0 10px rgba(239,68,68,0.7)';
          textEl.textContent = `${label} ${data.ip}: offline?`;
        }
      } catch (e) {
        dotEl.style.background = '#f97316';
        dotEl.style.boxShadow = '0 0 10px rgba(249,115,22,0.7)';
        textEl.textContent = `${label}: unknown`;
      }
    }
function refreshBadges() {
  refreshEspBadge(espIp, document.getElementById('esp1-dot'), document.getElementById('esp1-text'), 'ESP1');
  refreshEspBadge(esp2Ip, document.getElementById('esp2-dot'), document.getElementById('esp2-text'), 'ESP2');
  refreshEspBadge(esp3Ip, document.getElementById('esp3-dot'), document.getElementById('esp3-text'), 'ESP3');
}
    refreshBadges();
    setInterval(refreshBadges, 7000);
  </script>
</body>
</html>
"""

WEATHER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <title>Weather + Quickmenu</title>
  <style>
    :root {
      --bg: #050910;
      --card: #0f1626;
      --card-2: #0c1a2c;
      --accent: #ffb703;
      --accent-2: #22d3ee;
      --text: #e8edf7;
      --muted: #9fb0c8;
      --good: #34d399;
      --danger: #f87171;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(130% 90% at 10% 10%, #0f182d 0%, #050910 60%, #04070f 100%);
      font-family: "Segoe UI", "Helvetica Neue", system-ui, sans-serif;
      color: var(--text);
      display: flex;
      justify-content: center;
      overflow-y: auto;
      scrollbar-width: none;
      -ms-overflow-style: none;
    }
    body::-webkit-scrollbar { display: none; }
    .screen {
      width: min(520px, 96vw);
      min-height: 100vh;
      padding: 16px 14px 32px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .hero {
      min-height: 100vh;
      display:flex;
      flex-direction:column;
      align-items:flex-start;
      justify-content:center;
      gap:14px;
    }
    .eyebrow { text-transform: uppercase; letter-spacing: 1px; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
    .clock { font-size: 110px; font-weight: 800; letter-spacing: 1.6px; margin: 0; line-height: 0.95; }
    .muted { color: var(--muted); font-size: 16px; }
    .card {
      background: var(--card);
      border: 1px solid #1f2a44;
      border-radius: 18px;
      padding: 14px;
      margin-top: 12px;
      box-shadow: 0 12px 35px rgba(0,0,0,0.35);
    }
    .primary-card {
      background: linear-gradient(135deg, #0d1628, #0c1a2f);
      border: 1px solid #233454;
    }
    .chip {
      background: rgba(255,255,255,0.06);
      border: 1px solid #233454;
      border-radius: 999px;
      padding: 8px 12px;
      font-weight: 700;
      font-size: 13px;
    }
    .temp-row { display:flex; gap:14px; align-items:center; justify-content:flex-start; }
    .temp { font-size: 82px; font-weight: 800; letter-spacing: 0.5px; }
    .condition { font-size: 26px; font-weight: 800; }
    .pill {
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.08);
      border: 1px solid #233454;
      font-size: 13px;
      margin-right: 6px;
      margin-top: 8px;
      white-space: nowrap;
    }
    .pill.soft { background: rgba(255,255,255,0.04); }
    .meta-row { display:flex; flex-wrap:wrap; gap:6px; }
    .label { display:block; font-size: 13px; color: var(--muted); margin-bottom: 4px; }
    input {
      width: 100%;
      padding: 12px;
      border-radius: 12px;
      border: 1px solid #233454;
      background: #0a1322;
      color: var(--text);
      font-size: 18px;
    }
    input::placeholder { color: #637297; }
    .row { display:flex; gap:10px; flex-wrap:wrap; }
    .half { flex: 1 1 47%; }
    button {
      appearance: none;
      border: none;
      border-radius: 14px;
      padding: 14px 16px;
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 0.3px;
      color: #0a0d14;
      background: linear-gradient(135deg, var(--accent), #fca311);
      box-shadow: 0 10px 30px rgba(252, 163, 17, 0.35);
      cursor: pointer;
      width: 100%;
      touch-action: manipulation;
    }
    button:active { transform: translateY(1px); }
    .buttons button { flex: 1 1 48%; }
    .ghost {
      background: linear-gradient(135deg, #1c2c46, #14243c);
      color: var(--text);
      box-shadow: none;
    }
    .status { margin-top: 10px; }
    .small { font-size: 12px; margin-top: 6px; }
    .quickmenu-btn {
      width: 100%;
      background: linear-gradient(135deg, #22d3ee, #3b82f6);
      color: #041224;
    }
    .secondary-btn {
      width: 100%;
      background: linear-gradient(135deg, #f87171, #ef4444);
      color: #1b0b0b;
      box-shadow: 0 10px 30px rgba(239, 68, 68, 0.35);
    }
    .cta-wrap {
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: auto;
      padding-bottom: 8px;
    }
    @media (max-width: 540px) {
      .clock { font-size: 90px; }
      .temp { font-size: 70px; }
      .buttons { flex-direction: column; }
      .buttons button { width: 100%; }
    }
  </style>
</head>
<body>
  <div class="screen">
    <div class="hero">
      <div class="eyebrow">Local time</div>
      <div id="clock" class="clock">--:--</div>
      <div id="date" class="muted">Waiting…</div>
      <div class="temp-row">
        <div id="temp" class="temp">--°F</div>
        <div>
          <div id="condition" class="condition">Waiting for location…</div>
          <div id="location" class="muted">Location: —</div>
        </div>
      </div>
      <div class="chip">Portrait / 5"</div>
    </div>

    <div class="card primary-card">
      <div class="eyebrow">Details</div>
      <div class="meta-row">
        <div id="wind" class="pill">Wind --</div>
        <div id="humidity" class="pill">Humidity --</div>
        <div id="updated" class="pill">Updated --</div>
      </div>
      <div id="source" class="pill soft" style="margin-top:10px;">Source: offline/cache</div>
    </div>

    <div class="card">
      <div class="eyebrow">Pick a location</div>
      <div class="row">
        <div class="half">
          <label class="label" for="preset-select">Preset</label>
          <select id="preset-select" style="width:100%; padding:12px; border-radius:12px; border:1px solid #233454; background:#0a1322; color:var(--text); font-size:18px;">
            <option value="">Choose city</option>
            <option value="San Diego" data-lat="32.7157" data-lon="-117.1611">San Diego</option>
            <option value="Niland" data-lat="33.2378" data-lon="-115.5180">Niland</option>
            <option value="San Francisco" data-lat="37.7749" data-lon="-122.4194">San Francisco</option>
            <option value="Chicago" data-lat="41.8781" data-lon="-87.6298">Chicago</option>
            <option value="Detroit" data-lat="42.3314" data-lon="-83.0458">Detroit</option>
          </select>
        </div>
        <div class="half">
          <label class="label" for="location-input">Custom location</label>
          <input id="location-input" type="text" placeholder="Name">
        </div>
      </div>
      <div class="row" style="margin-top:10px;">
        <div class="half">
          <label class="label" for="lat-input">Latitude</label>
          <input id="lat-input" type="number" step="0.0001" inputmode="decimal" placeholder="33.0000">
        </div>
        <div class="half">
          <label class="label" for="lon-input">Longitude</label>
          <input id="lon-input" type="number" step="0.0001" inputmode="decimal" placeholder="-115.0000">
        </div>
      </div>
      <div class="row buttons" style="margin-top:12px;">
        <button class="ghost" onclick="useGps()">Use current location</button>
        <button onclick="refreshWeather()">Refresh weather</button>
      </div>
      <div id="status" class="muted status">Waiting for location…</div>
    </div>
    <div class="cta-wrap">
      <button class="quickmenu-btn" onclick="launchQuickmenu()">Launch Quickmenu</button>
      <button class="secondary-btn" onclick="closeChromium()">Close Chromium</button>
    </div>
  </div>
  <script>
    const quickmenuUrl = "{{ quickmenu_url }}";
    const serverCache = {{ last_weather|tojson }};
    const presets = [
      { name: 'San Diego', lat: 32.7157, lon: -117.1611 },
      { name: 'Niland', lat: 33.2378, lon: -115.5180 },
      { name: 'San Francisco', lat: 37.7749, lon: -122.4194 },
      { name: 'Chicago', lat: 41.8781, lon: -87.6298 },
      { name: 'Detroit', lat: 42.3314, lon: -83.0458 },
    ];

    const clockEl = document.getElementById('clock');
    const dateEl = document.getElementById('date');
    const tempEl = document.getElementById('temp');
    const conditionEl = document.getElementById('condition');
    const locationEl = document.getElementById('location');
    const windEl = document.getElementById('wind');
    const humidityEl = document.getElementById('humidity');
    const updatedEl = document.getElementById('updated');
    const sourceEl = document.getElementById('source');
    const statusEl = document.getElementById('status');
    const locationInput = document.getElementById('location-input');
    const latInput = document.getElementById('lat-input');
    const lonInput = document.getElementById('lon-input');
    const presetSelect = document.getElementById('preset-select');

    let latest = null;

    function setStatus(msg) {
      statusEl.textContent = msg;
    }

    function updateClock() {
      const now = new Date();
      clockEl.textContent = now.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
      dateEl.textContent = now.toLocaleDateString([], {weekday: 'short', month: 'short', day: 'numeric'});
    }
    updateClock();
    setInterval(updateClock, 1000);

    function fmtUpdated(ts) {
      try {
        const d = new Date(ts);
        return d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
      } catch (e) {
        return ts || '—';
      }
    }

    function persistLocal(data) {
      try { localStorage.setItem('weather_snapshot', JSON.stringify(data)); } catch (e) {}
    }
    function readLocal() {
      try {
        const raw = localStorage.getItem('weather_snapshot');
        if (raw) return JSON.parse(raw);
      } catch (e) {}
      return null;
    }

    function renderWeather(data, note) {
      if (!data) return;
      latest = data;
      const tempVal = typeof data.temp_f === 'number' ? Math.round(data.temp_f) : null;
      tempEl.textContent = tempVal !== null ? `${tempVal}°F` : '--°F';
      conditionEl.textContent = data.condition || 'Weather';
      locationEl.textContent = data.location ? `Location: ${data.location}` : 'Location: —';
      windEl.textContent = data.wind_mph !== null && data.wind_mph !== undefined ? `Wind ${Math.round(data.wind_mph)} mph` : 'Wind --';
      humidityEl.textContent = data.humidity !== null && data.humidity !== undefined ? `Humidity ${Math.round(data.humidity)}%` : 'Humidity --';
      updatedEl.textContent = data.updated ? `Updated ${fmtUpdated(data.updated)}` : 'Updated now';
      sourceEl.textContent = `Source: ${data.source || 'cache'}`;
      setStatus(note || `Weather updated (${data.source || 'cache'})`);
      persistLocal(data);
      if (data.location && !locationInput.value) locationInput.value = data.location;
      if (data.lat && data.lon) {
        latInput.value = Number(data.lat).toFixed(4);
        lonInput.value = Number(data.lon).toFixed(4);
      }
    }

    async function refreshWeather() {
      const lat = parseFloat(latInput.value);
      const lon = parseFloat(lonInput.value);
      const label = (locationInput.value || '').trim() || 'Your location';
      if (!isFinite(lat) || !isFinite(lon)) {
        setStatus('Pick a preset, enter coords, or tap current location.');
        return;
      }
      setStatus('Fetching weather…');
      try {
        const params = new URLSearchParams({ lat: lat.toString(), lon: lon.toString(), label });
        const res = await fetch(`/api/weather?${params.toString()}`);
        const data = await res.json();
        if (data && data.ok) {
          renderWeather(data, data.source === 'cache' ? 'Using cached weather' : 'Live weather fetched');
        } else {
          setStatus('Weather unavailable; using cached/manual if any.');
          const local = readLocal();
          if (local) renderWeather(local, 'Local cache');
        }
      } catch (e) {
        setStatus('Offline; showing cached/manual data.');
        const local = readLocal();
        if (local) renderWeather(local, 'Local cache');
      }
    }

    function useGps() {
      if (!navigator.geolocation) {
        setStatus('Geolocation not supported; type coords.');
        return;
      }
      setStatus('Requesting location…');
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords;
          latInput.value = latitude.toFixed(4);
          lonInput.value = longitude.toFixed(4);
          refreshWeather();
        },
        () => setStatus('Location blocked; type coords or use manual weather.')
      );
    }

    function launchQuickmenu() {
      window.location.href = quickmenuUrl || '/quickmenu';
    }

    async function closeChromium() {
      setStatus('Closing Chromium…');
      try {
        const res = await fetch('/api/close-chromium', { method: 'POST' });
        const data = await res.json();
        if (data && data.killed) {
          setStatus('Chromium closed');
        } else {
          setStatus('No Chromium window found');
        }
      } catch (e) {
        setStatus('Close Chromium failed');
      }
    }

    presetSelect.addEventListener('change', () => {
      const opt = presetSelect.options[presetSelect.selectedIndex];
      const lat = parseFloat(opt.getAttribute('data-lat'));
      const lon = parseFloat(opt.getAttribute('data-lon'));
      const name = opt.value || '';
      if (isFinite(lat) && isFinite(lon)) {
        latInput.value = lat.toFixed(4);
        lonInput.value = lon.toFixed(4);
        locationInput.value = name;
        refreshWeather();
      }
    });

    (function bootstrap() {
      const local = readLocal();
      const hasServerCache = serverCache && Object.keys(serverCache).length;
      if (hasServerCache) {
        renderWeather(serverCache, serverCache.source ? `Loaded ${serverCache.source}` : 'Loaded cached weather');
      } else if (local) {
        renderWeather(local, 'Loaded local cache');
      } else {
        setStatus('Enter a location or tap GPS.');
      }
      if (!hasServerCache) {
        // Try pulling cache from server in case it changed.
        fetch('/api/weather?cache_only=1')
          .then((res) => res.json())
          .then((data) => { if (data && data.ok) renderWeather(data, 'Loaded Pi cache'); })
          .catch(() => {});
      }
    })();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    start_default_watcher()
    start_esp3_default_watcher()
    # Apply default once on startup in case ESP is already online.
    try:
        apply_default_state()
    except Exception as exc:
        # Keep the web UI up even if MQTT/ESP is unreachable on boot.
        print(f"apply_default_state failed: {exc}")
    try:
        apply_default_esp3()
    except Exception as exc:
        print(f"apply_default_esp3 failed: {exc}")
    app.run(host="0.0.0.0", port=port, debug=False)
