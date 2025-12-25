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
from dataclasses import dataclass
from typing import Dict, List, Optional

from flask import Flask, jsonify, render_template_string, request
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "10.42.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER") or None
MQTT_PASS = os.getenv("MQTT_PASS") or None
MQTT_CMD_TOPIC = os.getenv("MQTT_CMD_TOPIC", "led/command")
STATES_FILE = os.getenv("LED_STATE_FILE", os.path.join(os.path.dirname(__file__), "led_states.json"))
SEGMENTS = [
    "strip0",
    "strip1",
    "strip2",
    "strip3",
    "seg250_323",
    "seg330_400",
]
SEGMENT_LABELS = {
    "strip1": "Main Surround Lights",
    "seg250_323": "Right Speaker",
    "seg330_400": "Left Speaker",
}
PATTERNS = ["solid", "rainbow", "sine", "wind_meter", "mic_vu"]
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
START_TIME = time.time()
ESP_DEFAULT_IP = os.getenv("ESP_IP", "10.42.0.13")
ESP2_DEFAULT_IP = os.getenv("ESP2_IP", "10.42.0.29")

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
LAST_DEFAULT_APPLY = 0.0
LAST_ESP_UP = False


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
        }
    )


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



HTML = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"UTF-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Funkytown Shoeport Pneumatic Funk</title>
<link href=\"https://fonts.googleapis.com/css2?family=Balsamiq+Sans:wght@400;700&family=DM+Mono:wght@400;500&display=swap\" rel=\"stylesheet\">
<style>
:root {
  --bg: #f3f1eb;
  --card: #fdfbf6;
  --accent: #ffcc33;
  --accent2: #ffe97f;
  --text: #111;
  --muted: #444;
  --border: #111;
  --shadow: 4px 4px 0 #111;
}
* { box-sizing: border-box; }
body {
  margin:0; padding:0; min-height:100vh;
  font-family: 'Balsamiq Sans', 'DM Mono', system-ui, -apple-system, sans-serif;
  background: repeating-linear-gradient(
    0deg,
    #f3f1eb,
    #f3f1eb 12px,
    #f7f5ef 12px,
    #f7f5ef 24px
  );
  color: var(--text);
  display:flex; align-items:center; justify-content:center;
}
.wrapper { width: min(980px, 94vw); margin: 24px auto; }
.hero { padding: 12px 6px; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
.badge { padding:8px 12px; border-radius:8px; background:var(--card); color:var(--text); font-size:14px; display:inline-flex; align-items:center; gap:8px; border:2px solid var(--border); box-shadow: var(--shadow); }
.status-dot { width:12px; height:12px; border-radius:4px; background:#1a1a1a; box-shadow:0 0 0 2px #111; transition: background 0.2s ease, box-shadow 0.2s ease; }
.card { background: var(--card); border: 2px solid var(--border); border-radius: 14px; box-shadow: var(--shadow); padding: 16px; }
.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:16px; margin-top:10px; }
.field label { font-size:13px; color: var(--muted); margin-bottom:6px; display:block; letter-spacing:0.2px; }
.field input, .field select { width:100%; padding:12px; border-radius:8px; border:2px solid var(--border); background: #fff; color: var(--text); font-size:17px; font-family:'DM Mono', monospace; box-shadow: inset 2px 2px 0 #ddd; }
.range { display:flex; align-items:center; gap:10px; }
.range output { min-width:48px; text-align:right; font-variant-numeric: tabular-nums; }
button { border:2px solid #111; border-radius:10px; padding:12px 16px; font-size:17px; font-weight:700; letter-spacing:0.3px; color:#111; cursor:pointer; transition:transform 0.08s ease, box-shadow 0.1s ease; background: var(--accent); box-shadow: 4px 4px 0 #111; }
button:active { transform: translateY(1px); box-shadow: 2px 2px 0 #111; }
.btn-secondary { background: #fff; }
.footer { margin-top:14px; font-size:13px; color: var(--muted); text-align:center; }
.pill { padding:6px 10px; border-radius:999px; border:1px solid var(--border); font-size:12px; display:inline-flex; gap:6px; align-items:center; }
.rainbow { position:absolute; inset: -2px; border-radius: 18px; background: conic-gradient(from 90deg, #ff7fe5, #7cffe2, #7fb3ff, #ffcf7f, #ff7fe5); filter: blur(18px); opacity:0.25; z-index:-1; }
.card-wrap { position:relative; }
.troubleshoot { margin-top:18px; padding:14px; border-radius:14px; border:1px dashed var(--border); background: rgba(255,255,255,0.04); }
.troubleshoot pre { background: rgba(0,0,0,0.25); padding:10px; border-radius:10px; color: var(--text); font-size:13px; overflow-x:auto; }
@media (max-width: 720px) {
  body { padding: 10px; align-items:flex-start; }
  .hero { flex-direction:column; align-items:flex-start; }
  .badge { font-size:12px; }
  .field input, .field select { font-size:16px; }
  button { width:100%; justify-content:center; text-align:center; }
}
</style>
</head>
<body>
  <div class=\"wrapper\">
    <div class=\"hero\">
      <div>
        <div class=\"pill\">MQTT: {{ mqtt_host }} · {{ mqtt_topic }}</div>
        <h1 style=\"margin:6px 0 0; font-size:30px;\">Funkytown shoe port</h1>
        <p style=\"margin:4px 0 0; color:var(--muted);\">LED control on HotMess — tune each segment independently.</p>
      </div>
      <div style=\"display:flex; gap:10px; align-items:center; flex-wrap:wrap; justify-content:flex-end;\">
        <button class=\"btn-secondary\" style=\"padding:10px 12px;\" onclick=\"lightsOff()\">All Off</button>
        <button style=\"padding:10px 12px; background:#d4ffb5;\" onclick=\"lightsOn()\">All On</button>
        <div class=\"badge\" id=\"svc-badge\"><span class=\"status-dot\" id=\"svc-dot\"></span><span id=\"svc-text\">Service: …</span></div>
        <div class=\"badge\" id=\"esp-badge\"><span class=\"status-dot\" id=\"esp-dot\" style=\"background:#f2a900; box-shadow:0 0 10px #f2a900;\"></span><span id=\"esp-text\">ESP: …</span></div>
        <div class=\"badge\" id=\"esp2-badge\"><span class=\"status-dot\" id=\"esp2-dot\" style=\"background:#f2a900; box-shadow:0 0 10px #f2a900;\"></span><span id=\"esp2-text\">ESP2: …</span></div>
        <div class=\"badge\" id=\"pi-badge\"><span class=\"status-dot\" id=\"pi-dot\"></span><span id=\"pi-text\">Pi temp: …</span></div>
      </div>
    </div>
    <div class=\"card-wrap\">
      <div class=\"rainbow\"></div>
      <div class=\"card\">
        <div class=\"grid\">
      <div class=\"field\">
        <label>Segment</label>
        <select id=\"segment\" onchange=\"loadSegmentFromState()\">{% for s in segments %}<option value=\"{{s}}\">{{ segment_labels.get(s, s) }}</option>{% endfor %}</select>
      </div>
          <div class=\"field\">
            <label>Pattern</label>
            <select id=\"pattern\">{% for p in patterns %}<option value=\"{{p}}\">{{p}}</option>{% endfor %}</select>
          </div>
          <div class=\"field\">
            <label>Brightness (0-255)</label>
            <div class=\"range\">
              <input id=\"brightness\" type=\"range\" min=\"0\" max=\"255\" value=\"180\" oninput=\"bOut.textContent=this.value\">
              <output id=\"bOut\">180</output>
            </div>
          </div>
          <div class=\"field\">
            <label>Speed</label>
            <div class=\"range\">
              <input id=\"speed\" type=\"range\" min=\"0\" max=\"5\" step=\"0.1\" value=\"1.0\" oninput=\"sOut.textContent=this.value\">
              <output id=\"sOut\">1.0</output>
            </div>
          </div>
      <div class=\"field\">
        <label>Wave Shape (sine/square/triangle)</label>
        <select id=\"wave_shape\">
          <option value=\"\">(none)</option>
          <option value=\"sine\">sine</option>
              <option value=\"square\">square</option>
              <option value=\"triangle\">triangle</option>
            </select>
      </div>
      <div class=\"field\">
        <label>Rainbow Waves</label>
        <div class=\"range\">
          <input id=\"wave_count\" type=\"range\" min=\"0\" max=\"50\" step=\"1\" value=\"5\" oninput=\"wcOut.textContent=this.value\">
          <output id=\"wcOut\">5</output>
        </div>
        <p style=\"margin:4px 0 0; color:var(--muted); font-size:12px;\">Higher = denser rainbow bands.</p>
      </div>
      <div class=\"field card\" style=\"margin-top:6px; background: #fffbe6;\">
        <div style=\"display:flex; align-items:center; justify-content:space-between; gap:8px;\">
          <label style=\"margin:0; font-weight:700;\">Mic (audio reactive)</label>
          <span class=\"pill\" style=\"background:#fff;\">mic_vu</span>
        </div>
        <div class=\"range\" style=\"margin-top:8px;\">
          <label style=\"font-size:13px; color:var(--muted);\">Mic Gain</label>
          <input id=\"mic_gain\" type=\"range\" min=\"-1\" max=\"1\" step=\"0.1\" value=\"0.3\" oninput=\"mgOut.textContent=this.value\">
          <output id=\"mgOut\">0.3</output>
        </div>
        <div class=\"range\" style=\"margin-top:8px;\">
          <label style=\"font-size:13px; color:var(--muted);\">Mic Floor</label>
          <input id=\"mic_floor\" type=\"range\" min=\"0\" max=\"0.2\" step=\"0.01\" value=\"0.02\" oninput=\"mfOut.textContent=this.value\">
          <output id=\"mfOut\">0.02</output>
        </div>
        <div class=\"range\" style=\"margin-top:8px;\">
          <label style=\"font-size:13px; color:var(--muted);\">Mic Smooth</label>
          <input id=\"mic_smooth\" type=\"range\" min=\"0\" max=\"0.6\" step=\"0.01\" value=\"0.3\" oninput=\"msOut.textContent=this.value\">
          <output id=\"msOut\">0.3</output>
        </div>
        <p style=\"margin:4px 0 4px; color:var(--muted); font-size:12px;\">Higher smooth = slower response.</p>
        <div style=\"display:flex; align-items:center; gap:10px; margin-top:6px;\">
          <input id=\"mic_enabled\" type=\"checkbox\" checked>
          <label for=\"mic_enabled\" style=\"margin:0;\">Audio-reactive enabled</label>
        </div>
        <div style=\"display:flex; align-items:center; gap:10px; margin-top:6px;\">
          <input id=\"mic_beat\" type=\"checkbox\">
          <label for=\"mic_beat\" style=\"margin:0;\">Beat mode (peaks only)</label>
        </div>
      </div>
      <div class=\"field\">
        <label>Color</label>
        <select id=\"color_select\" onchange=\"toggleGradientBox()\">
          <option value=\"\">(choose color)</option>
          {% for name, rgb in colors %}
          <option value=\"{{name}}\" data-rgb=\"{{rgb[0]}},{{rgb[1]}},{{rgb[2]}}\">{{name}}</option>
          {% endfor %}
          <option value=\"__gradient__\">Audio Reactive Gradients…</option>
        </select>
      </div>
      <div class=\"field\" id=\"gradient_box\" style=\"display:none;\">
        <label>Gradient Palette (low→mid→high)</label>
        <select id=\"gradient_select\">
          {% for name, low, mid, high in gradients %}
          <option value=\"{{loop.index0}}\" data-low=\"{{low[0]}},{{low[1]}},{{low[2]}}\" data-mid=\"{{mid[0]}},{{mid[1]}},{{mid[2]}}\" data-high=\"{{high[0]}},{{high[1]}},{{high[2]}}\">{{name}}</option>
          {% endfor %}
        </select>
        <p style=\"margin:4px 0 0; color:var(--muted); font-size:12px;\">Used for mic_vu when gradient mode is selected.</p>
      </div>
        </div>
        <div class=\"grid\" style=\"margin-top:14px; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));\">
          <button onclick=\"sendCmd()\">Send Pattern</button>
          <button class=\"btn-secondary\" onclick=\"sendPing()\">Ping Segment</button>
        </div>
      </div>
    </div>
    <div class=\"card\" style=\"margin-top:12px;\">
      <h3 style=\"margin:0 0 8px;\">States</h3>
      <div id=\"state-grid\" class=\"grid\" style=\"grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));\"></div>
    </div>
    <div class=\"card\" style=\"margin-top:12px;\">
      <h3 style=\"margin:0 0 8px;\">Global Brightness</h3>
      <div class=\"field\">
        <label>All Segments Brightness</label>
        <div class=\"range\">
          <input id=\"gbrightness\" type=\"range\" min=\"0\" max=\"255\" value=\"180\" oninput=\"gbOut.textContent=this.value\">
          <output id=\"gbOut\">180</output>
        </div>
      </div>
      <div class=\"grid\" style=\"margin-top:10px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));\">
        <button onclick=\"sendGlobalBrightness()\">Apply</button>
        <button class=\"btn-secondary\" onclick=\"applyPreset('calm')\">Preset: Calm</button>
        <button class=\"btn-secondary\" onclick=\"applyPreset('rainbow')\">Preset: Rainbow</button>
        <button class=\"btn-secondary\" onclick=\"applyPreset('white')\">Preset: White</button>
        <button style=\"background:#ffd1d1;\" onclick=\"lightsOff()\">Lights Off</button>
        <button style=\"background:#d4ffb5;\" onclick=\"lightsOn()\">Lights On (default)</button>
      </div>
    </div>
    <div class=\"card\" style=\"margin-top:14px;\">
      <div style=\"display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;\">
        <div>
          <strong>Saved states</strong>
          <p style=\"margin:4px 0; color:var(--muted); font-size:13px;\">Store segment, pattern, brightness, speed, color, and wave shape.</p>
          <div id=\"default-label\" class=\"pill\" style=\"margin-top:6px;\">Default: none</div>
        </div>
        <div style=\"display:flex; gap:10px; align-items:center; flex-wrap:wrap;\">
          <input id=\"state-name\" type=\"text\" placeholder=\"Name (e.g. Party)\" style=\"padding:10px 12px; border-radius:10px; border:1px solid var(--border); font-size:14px; min-width:160px;\">
          <button class=\"btn-secondary\" onclick=\"saveState()\">Save current</button>
        </div>
      </div>
      <div class=\"grid\" style=\"margin-top:12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); align-items:end;\">
        <div class=\"field\">
          <label>Saved presets</label>
          <select id=\"state-select\"></select>
        </div>
        <button onclick=\"applyState()\">Apply state</button>
        <button class=\"btn-secondary\" onclick=\"setDefaultState()\">Set as default</button>
        <button class=\"btn-secondary\" onclick=\"loadStateIntoForm()\">Load into form</button>
        <button class=\"btn-secondary\" style=\"background:#ffd1d1;\" onclick=\"deleteState()\">Delete</button>
      </div>
    </div>
    <div class=\"troubleshoot\">
      <div style=\"display:flex; align-items:center; gap:10px; justify-content:space-between; flex-wrap:wrap;\">
        <div>
          <strong>Troubleshoot ESP</strong>
          <p style=\"margin:4px 0; color:var(--muted); font-size:13px;\">Checks MQTT and pings the ESP (default {{ esp_default_ip }}).</p>
        </div>
        <button class=\"btn-secondary\" onclick=\"runTroubleshoot()\">Run Checks</button>
      </div>
      <pre id=\"ts-output\">Waiting…</pre>
    </div>
    <div class=\"footer\" id=\"uptime\"></div>
  </div>
<script>
async function sendCmd() {
  const gradient = getGradientSelection();
  const payload = {
    segment: document.getElementById('segment').value,
    pattern: document.getElementById('pattern').value,
    brightness: parseFloat(document.getElementById('brightness').value || '0'),
    speed: parseFloat(document.getElementById('speed').value || '0'),
    color: getSelectedColor(),
    wave_shape: document.getElementById('wave_shape').value || undefined,
    wave_count: parseFloat(document.getElementById('wave_count').value || '0'),
    mic_gain: parseFloat(document.getElementById('mic_gain').value || '0'),
    mic_floor: parseFloat(document.getElementById('mic_floor').value || '0'),
    mic_smooth: parseFloat(document.getElementById('mic_smooth').value || '0'),
    mic_enabled: document.getElementById('mic_enabled').checked,
    mic_beat: document.getElementById('mic_beat').checked,
  };
  if (gradient) {
    payload.gradient_low = gradient.low;
    payload.gradient_mid = gradient.mid;
    payload.gradient_high = gradient.high;
    payload.gradient_enabled = true;
  } else {
    payload.gradient_enabled = false;
  }
  await fetch('/api/set', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
}
async function sendPing() {
  const payload = { segment: document.getElementById('segment').value };
  await fetch('/api/ping', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
}
async function sendGlobalBrightness() {
  const val = parseFloat(document.getElementById('gbrightness').value || '0');
  await fetch('/api/set-all', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({brightness: val})});
  refreshState();
}

async function lightsOff() {
  await fetch('/api/set-all', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({brightness: 0})});
  document.getElementById('gbrightness').value = 0;
  document.getElementById('gbOut').textContent = 0;
  refreshState();
}

async function lightsOn() {
  // Apply default if it exists; otherwise set to a gentle brightness.
  const res = await fetch('/api/state/apply-default', {method:'POST'});
  try {
    const data = await res.json();
    if (!data.ok) {
      await fetch('/api/set-all', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({brightness: 180})});
    }
  } catch (e) {
    await fetch('/api/set-all', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({brightness: 180})});
  }
  document.getElementById('gbrightness').value = 180;
  document.getElementById('gbOut').textContent = 180;
  refreshState();
}
const stateCache = {};
let defaultStateName = null;
const liveState = {};
const gradientPalettes = {{ gradients|tojson }};
const esp2Ip = "{{ esp2_default_ip }}";

function currentPayloadFromForm() {
  const gradient = getGradientSelection();
  return {
    segment: document.getElementById('segment').value,
    pattern: document.getElementById('pattern').value,
    brightness: parseFloat(document.getElementById('brightness').value || '0'),
    speed: parseFloat(document.getElementById('speed').value || '0'),
    color: getSelectedColor(),
    wave_shape: document.getElementById('wave_shape').value || undefined,
    wave_count: parseFloat(document.getElementById('wave_count').value || '0'),
    mic_gain: parseFloat(document.getElementById('mic_gain').value || '0'),
    mic_floor: parseFloat(document.getElementById('mic_floor').value || '0'),
    mic_smooth: parseFloat(document.getElementById('mic_smooth').value || '0'),
    mic_enabled: document.getElementById('mic_enabled').checked,
    mic_beat: document.getElementById('mic_beat').checked,
    gradient_low: gradient ? gradient.low : undefined,
    gradient_mid: gradient ? gradient.mid : undefined,
    gradient_high: gradient ? gradient.high : undefined,
    gradient_enabled: !!gradient,
  };
}

function loadStateIntoForm() {
  const sel = document.getElementById('state-select');
  const name = sel.value;
  if (!name || !stateCache[name]) return;
  const entry = stateCache[name];
  const data = entry.segments ? Object.values(entry.segments)[0] || {} : entry;
  document.getElementById('segment').value = data.segment || 'strip1';
  document.getElementById('pattern').value = data.pattern || 'solid';
  document.getElementById('brightness').value = data.brightness ?? 180;
  document.getElementById('bOut').textContent = data.brightness ?? 180;
  document.getElementById('speed').value = data.speed ?? 1.0;
  document.getElementById('sOut').textContent = data.speed ?? 1.0;
  document.getElementById('wave_shape').value = data.wave_shape || '';
  const c = data.color || [0,180,160];
  setSelectedColor(c);
  if (data.wave_count !== undefined) {
    document.getElementById('wave_count').value = data.wave_count;
    document.getElementById('wcOut').textContent = data.wave_count;
  }
  if (data.mic_gain !== undefined) {
    document.getElementById('mic_gain').value = data.mic_gain;
    document.getElementById('mgOut').textContent = data.mic_gain;
  }
  if (data.mic_floor !== undefined) {
    document.getElementById('mic_floor').value = data.mic_floor;
    document.getElementById('mfOut').textContent = data.mic_floor;
  }
  if (data.mic_smooth !== undefined) {
    document.getElementById('mic_smooth').value = data.mic_smooth;
    document.getElementById('msOut').textContent = data.mic_smooth;
  }
  if (data.mic_enabled !== undefined) {
    document.getElementById('mic_enabled').checked = !!data.mic_enabled;
  }
  if (data.mic_beat !== undefined) {
    document.getElementById('mic_beat').checked = !!data.mic_beat;
  }
  if (data.gradient_enabled) {
    const low = data.gradient_low || [0,0,0];
    const mid = data.gradient_mid || [0,0,0];
    const high = data.gradient_high || [0,0,0];
    setGradientSelection(low, mid, high);
    document.getElementById('color_select').value = '__gradient__';
    toggleGradientBox();
  } else {
    setSelectedColor(data.color || [0,180,160]);
  }
}

async function refreshStatesList() {
  try {
    const res = await fetch('/api/states');
    const data = await res.json();
    const sel = document.getElementById('state-select');
    sel.innerHTML = '';
    Object.keys(stateCache).forEach((k) => delete stateCache[k]);
    (data.states || []).forEach((s) => {
      stateCache[s.name] = s.data;
      const opt = document.createElement('option');
      opt.value = s.name;
      opt.textContent = s.name;
      sel.appendChild(opt);
    });
    defaultStateName = data.default || null;
    const label = document.getElementById('default-label');
    if (label) label.textContent = `Default: ${defaultStateName || 'none'}`;
    if (defaultStateName && sel.options.length) {
      sel.value = defaultStateName;
    }
  } catch (e) {
    // ignore
  }
}

async function saveState() {
  const name = (document.getElementById('state-name').value || '').trim();
  if (!name) return;
  await fetch('/api/state/save', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
  await refreshStatesList();
  document.getElementById('state-select').value = name;
}

async function applyState() {
  const sel = document.getElementById('state-select');
  const name = sel.value;
  if (!name) return;
  try {
    const res = await fetch('/api/state/apply', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
    const data = await res.json();
    if (data && data.state && data.state.data) {
      stateCache[name] = data.state.data;
      loadStateIntoForm();
    }
  } catch (e) {
    // ignore
  }
}
async function setDefaultState() {
  const sel = document.getElementById('state-select');
  const name = sel.value;
  if (!name) return;
  await fetch('/api/state/default', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
  defaultStateName = name;
  const label = document.getElementById('default-label');
  if (label) label.textContent = `Default: ${defaultStateName}`;
  // Apply immediately so the lights match the chosen default.
  await applyState();
}
async function deleteState() {
  const sel = document.getElementById('state-select');
  const name = sel.value;
  if (!name) return;
  const sure = window.confirm(`Delete preset "${name}"?`);
  if (!sure) return;
  await fetch('/api/state/delete', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
  await refreshStatesList();
}
async function sendGlobalBrightness() {
  const val = parseFloat(document.getElementById('gbrightness').value || '0');
  await fetch('/api/set-all', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({brightness: val})});
  refreshState();
}

async function refreshStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    document.getElementById('svc-text').textContent = `Service: ${data.service}`;
    document.getElementById('svc-dot').style.background = '#00c853';
    document.getElementById('svc-dot').style.boxShadow = '0 0 12px #00c853';
    document.getElementById('uptime').textContent = `Uptime: ${data.uptime_seconds}s`;
  } catch (e) {
    document.getElementById('svc-text').textContent = 'Service: unknown';
    document.getElementById('svc-dot').style.background = '#ff7f7f';
    document.getElementById('svc-dot').style.boxShadow = '0 0 12px #ff7f7f';
  }
}
refreshStatus();
setInterval(refreshStatus, 5000);
// Initialize outputs to match defaults.
document.getElementById('sOut').textContent = document.getElementById('speed').value;
document.getElementById('wcOut').textContent = document.getElementById('wave_count').value;
document.getElementById('mgOut').textContent = document.getElementById('mic_gain').value;
document.getElementById('mfOut').textContent = document.getElementById('mic_floor').value;
document.getElementById('msOut').textContent = document.getElementById('mic_smooth').value;
document.getElementById('mic_enabled').checked = true;
toggleGradientBox();
// Load current segment once on page load so the form matches live state.
loadSegmentFromState();

async function refreshEsp() {
  try {
    const res = await fetch('/api/esp-status');
    const data = await res.json();
    if (data.reachable) {
      document.getElementById('esp-text').textContent = `ESP ${data.ip}: online`;
      document.getElementById('esp-dot').style.background = '#00c853';
      document.getElementById('esp-dot').style.boxShadow = '0 0 12px #00c853';
    } else {
      document.getElementById('esp-text').textContent = `ESP ${data.ip}: offline?`;
      document.getElementById('esp-dot').style.background = '#ff7f7f';
      document.getElementById('esp-dot').style.boxShadow = '0 0 12px #ff7f7f';
    }
  } catch (e) {
    document.getElementById('esp-text').textContent = 'ESP: unknown';
    document.getElementById('esp-dot').style.background = '#ff7f7f';
    document.getElementById('esp-dot').style.boxShadow = '0 0 12px #ff7f7f';
  }
}
refreshEsp();
setInterval(refreshEsp, 7000);
refreshStatesList();
refreshState();
async function refreshEsp2() {
  const dot = document.getElementById('esp2-dot');
  const text = document.getElementById('esp2-text');
  try {
    const res = await fetch(`/api/esp-status?ip=${esp2Ip}`);
    const data = await res.json();
    if (data.reachable) {
      text.textContent = `ESP2 ${data.ip}: online`;
      dot.style.background = '#00c853';
      dot.style.boxShadow = '0 0 12px #00c853';
    } else {
      text.textContent = `ESP2 ${data.ip}: offline?`;
      dot.style.background = '#ff7f7f';
      dot.style.boxShadow = '0 0 12px #ff7f7f';
    }
  } catch (e) {
    text.textContent = 'ESP2: unknown';
    dot.style.background = '#ff7f7f';
    dot.style.boxShadow = '0 0 12px #ff7f7f';
  }
}
refreshEsp2();
setInterval(refreshEsp2, 7000);

function renderStateGrid(list) {
  const grid = document.getElementById('state-grid');
  if (!grid) return;
  grid.innerHTML = '';
  Object.keys(liveState).forEach(k => delete liveState[k]);
  list.forEach(s => {
    liveState[s.segment] = s;
    const box = document.createElement('div');
    box.className = 'card';
    box.style.boxShadow = 'none';
    const style = stateBackgroundStyle(s);
    if (style) box.style.background = style;
    box.innerHTML = `<strong>${displayLabel(s.segment)}</strong><br>Pattern: ${s.pattern}`;
    grid.appendChild(box);
  });
}

async function refreshState() {
  try {
    const res = await fetch('/api/state');
    const data = await res.json();
    renderStateGrid(data.state || []);
  } catch (e) {
    // ignore
  }
}
setInterval(refreshState, 5000);

function applyPreset(name) {
  let payloads = [];
  if (name === 'calm') {
    payloads = [{pattern:'sine', brightness:120, speed:0.5, color:[255,200,80]}];
  } else if (name === 'rainbow') {
    payloads = [{pattern:'rainbow', brightness:200, speed:1.2}];
  } else if (name === 'white') {
    payloads = [{pattern:'solid', brightness:220, color:[255,255,255]}];
  }
  payloads.forEach(p => sendGlobal(p));
}

async function sendGlobal(p) {
  const body = {brightness: p.brightness, speed: p.speed, color: p.color, wave_shape: p.wave_shape};
  await fetch('/api/set-all', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  refreshState();
}

async function refreshPiTemp() {
  const dot = document.getElementById('pi-dot');
  const text = document.getElementById('pi-text');
  try {
    const res = await fetch('/api/pi-temp');
    const data = await res.json();
    if (data && data.ok && data.temp_c !== null && data.temp_c !== undefined) {
      const t = data.temp_c;
      text.textContent = `Pi temp: ${t}°C`;
      let color = '#00c853';
      let glow = '0 0 12px #00c853';
      if (t >= 65) { color = '#ff7f7f'; glow = '0 0 12px #ff7f7f'; }
      else if (t >= 55) { color = '#f2a900'; glow = '0 0 12px #f2a900'; }
      dot.style.background = color;
      dot.style.boxShadow = glow;
      return;
    }
  } catch (e) {
    // handled below
  }
  text.textContent = 'Pi temp: unknown';
  dot.style.background = '#ff7f7f';
  dot.style.boxShadow = '0 0 12px #ff7f7f';
}
refreshPiTemp();
setInterval(refreshPiTemp, 6000);

async function runTroubleshoot() {
  const out = document.getElementById('ts-output');
  out.textContent = 'Running checks...';
  try {
    const res = await fetch('/api/troubleshoot');
    const data = await res.json();
    const lines = [];
    lines.push(`ESP ${data.esp_ip}: ${data.esp_reachable ? 'reachable ✅' : 'unreachable ⚠️'}`);
    lines.push(`MQTT: ${data.mqtt_reachable ? 'reachable ✅' : 'unreachable ⚠️'}`);
    lines.push(`AP wlan0: ${data.wlan.up ? 'up ✅' : 'down ⚠️'} ${data.wlan.ip ? '('+data.wlan.ip+')' : ''}`);
    lines.push(`Mosquitto restart: ${data.mosquitto_restarted ? 'OK' : 'failed'}`);
    lines.push(`ESP reset (USB): ${data.esp_reset_attempted ? 'attempted' : 'not attempted'}`);
    if (data.suggestions && data.suggestions.length) {
      lines.push('Suggestions:');
      data.suggestions.forEach((s, i) => lines.push(`  ${i+1}. ${s}`));
    }
    out.textContent = lines.join('\\n');
  } catch (e) {
    out.textContent = 'Troubleshoot failed.';
  }
}

function loadSegmentFromState() {
  const seg = document.getElementById('segment').value;
  const s = liveState[seg];
  if (!s) return;
  document.getElementById('pattern').value = s.pattern || 'solid';
  document.getElementById('brightness').value = s.brightness ?? 180;
  document.getElementById('bOut').textContent = s.brightness ?? 180;
  document.getElementById('speed').value = s.speed ?? 1.0;
  document.getElementById('sOut').textContent = s.speed ?? 1.0;
  document.getElementById('wave_shape').value = s.wave_shape || '';
  if (s.wave_count !== undefined) {
    document.getElementById('wave_count').value = s.wave_count;
    document.getElementById('wcOut').textContent = s.wave_count;
  }
  if (s.gradient_enabled && s.gradient_low && s.gradient_mid && s.gradient_high) {
    setGradientSelection(s.gradient_low, s.gradient_mid, s.gradient_high);
    document.getElementById('color_select').value = '__gradient__';
    toggleGradientBox();
  } else if (s.color) {
    setSelectedColor(s.color);
  }
}

function getSelectedColor() {
  const sel = document.getElementById('color_select');
  const opt = sel.options[sel.selectedIndex];
  const parts = (opt.getAttribute('data-rgb') || '0,0,0').split(',').map(x => parseInt(x.trim(), 10));
  return [parts[0] || 0, parts[1] || 0, parts[2] || 0];
}
function getGradientSelection() {
  const colorSel = document.getElementById('color_select');
  if (colorSel.value !== '__gradient__') return null;
  const gsel = document.getElementById('gradient_select');
  const opt = gsel.options[gsel.selectedIndex];
  const low = (opt.getAttribute('data-low') || '0,0,0').split(',').map(x => parseInt(x, 10));
  const mid = (opt.getAttribute('data-mid') || '0,0,0').split(',').map(x => parseInt(x, 10));
  const high = (opt.getAttribute('data-high') || '0,0,0').split(',').map(x => parseInt(x, 10));
  return {low, mid, high};
}
function setGradientSelection(low, mid, high) {
  const gsel = document.getElementById('gradient_select');
  const target = [low, mid, high].map(arr => (arr || []).join(','));
  for (let i=0;i<gsel.options.length;i++) {
    const opt = gsel.options[i];
    if ((opt.getAttribute('data-low')||'') === target[0] &&
        (opt.getAttribute('data-mid')||'') === target[1] &&
        (opt.getAttribute('data-high')||'') === target[2]) {
      gsel.selectedIndex = i;
      return;
    }
  }
  gsel.selectedIndex = 0;
}
function toggleGradientBox() {
  const box = document.getElementById('gradient_box');
  const sel = document.getElementById('color_select');
  box.style.display = sel.value === '__gradient__' ? 'block' : 'none';
}
function setSelectedColor(rgb) {
  const sel = document.getElementById('color_select');
  const target = (rgb || []).join(',');
  for (let i=0;i<sel.options.length;i++) {
    if ((sel.options[i].getAttribute('data-rgb') || '') === target) {
      sel.selectedIndex = i;
      toggleGradientBox();
      return;
    }
  }
  // If not found, switch to gradient mode.
  sel.value = '__gradient__';
  toggleGradientBox();
}
function displayLabel(seg) {
  const map = {{ segment_labels|tojson }};
  return map[seg] || seg;
}
function stateBackgroundStyle(s) {
  if (!s) return '';
  if (s.pattern === 'rainbow') return 'linear-gradient(90deg, red, orange, yellow, green, cyan, blue, violet)';
  if (s.pattern === 'sine') return 'linear-gradient(135deg, #fef3c7, #c7d2fe)';
  if (s.pattern === 'wind_meter') return 'linear-gradient(135deg, #d1fae5, #bfdbfe)';
  if (s.pattern === 'mic_vu') {
    if (s.gradient_enabled && s.gradient_low && s.gradient_mid && s.gradient_high) {
      return `linear-gradient(90deg, rgb(${s.gradient_low.join(',')}), rgb(${s.gradient_mid.join(',')}), rgb(${s.gradient_high.join(',')}))`;
    }
    return 'linear-gradient(135deg, #fff3cd, #ffd6a5)';
  }
  if (s.pattern === 'solid' && s.color && s.color.length === 3) {
    return `rgb(${s.color[0]}, ${s.color[1]}, ${s.color[2]})`;
  }
  return '';
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    start_default_watcher()
    # Apply default once on startup in case ESP is already online.
    try:
        apply_default_state()
    except Exception as exc:
        # Keep the web UI up even if MQTT/ESP is unreachable on boot.
        print(f"apply_default_state failed: {exc}")
    app.run(host="0.0.0.0", port=port, debug=False)
