# Host Scripts (Raspberry Pi / PC)

Control the ESP32 LED firmware from a computer using the command-line helper or the Flask-based web UI.

## Contents
- `esp32_led_control.py` — CLI helper that publishes MQTT JSON commands to the ESP32 firmware.
- `led_web.py` — Local web UI + API that sends the same MQTT commands and remembers recent state.
- `led_states.json` — Saved default values the web UI loads at startup.
- `requirements.txt` — Python dependencies for both tools.

## Prerequisites
- Python 3.9+ with `pip`
- MQTT broker reachable by both the Pi/PC and the ESP32 (e.g., Mosquitto)

## Setup
```bash
cd host
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# optional: export MQTT env vars so both tools share them
export MQTT_HOST=10.42.0.1
export MQTT_PORT=1883
export MQTT_CMD_TOPIC=led/command
export MQTT_USER=youruser
export MQTT_PASS=yourpass
```

## CLI usage (`esp32_led_control.py`)
Set a pattern:
```bash
python esp32_led_control.py --host 10.42.0.1 set \
  --segment strip1 --pattern rainbow --brightness 0.6 --speed 1.2
```
Send a ping:
```bash
python esp32_led_control.py --host 10.42.0.1 ping
```
Flags map directly to the ESP32 JSON protocol (`cmd:set/ping`, `pattern`, `brightness`, `speed`, optional `segment`, and extra params like `--wave-shape`).

## Web UI (`led_web.py`)
Launch a small Flask app that serves a mobile-friendly control page and publishes MQTT messages on changes:
```bash
python led_web.py
```
- Uses `LED_STATE_FILE` (defaults to `./led_states.json`) to remember the last sent values.
- Reads the same MQTT env vars as the CLI.
- Visits to `/` render the control UI; `/status` returns last-known values for the UI.

## Quick troubleshooting
- If the ESP32 does not react, confirm it is subscribed to `MQTT_CMD_TOPIC` and shares the same broker IP.
- For auth errors, export `MQTT_USER`/`MQTT_PASS` or pass `--username/--password` to the CLI.
- To reset defaults, delete `led_states.json` so the app regenerates it.
