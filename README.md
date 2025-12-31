# ESP32 LED Control Kit (Firmware + Web UI)

Bundle of the ESP32 firmware, MQTT control helper, and a colorful web UI so you can flash the board, drive the LEDs from a Raspberry Pi/PC, and share the package with other LLMs.

## Repo layout
- `firmware/`
  - `esp32_firmware.ino` — main multi-segment LED engine (MQTT-driven).
  - `esp32u_camming/` — dedicated ESP32U firmware for the two “camming lights” strips (white/rainbow/hills, OTA ready).
- `host/` — Python CLI + Flask web UI (now includes a camming card + presets) that publish the same MQTT JSON commands to the ESP32s.

## Quick start
1) **Flash the firmware**
- Edit Wi-Fi, MQTT, and LED pin/length config in `firmware/esp32_firmware.ino`.
- Follow `firmware/README.md` for `arduino-cli` install, compile, and USB/OTA upload commands.

2) **Run host controls (Pi/PC)**
- `cd host && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Export MQTT settings or pass flags (`MQTT_HOST`, `MQTT_PORT`, optional `MQTT_USER`/`MQTT_PASS`, `MQTT_CMD_TOPIC`).
- CLI example: `python esp32_led_control.py --host 10.42.0.1 set --segment strip1 --pattern rainbow --brightness 0.6 --speed 1.2`
- Web UI: `python led_web.py` then open `http://localhost:5000/` to tweak segments and patterns (state saved to `led_states.json`; camming presets saved to `esp3_states.json`).

## MQTT protocol (ESP32 <-> host)
- Command topic defaults to `led/command` and expects JSON like:
```json
{"cmd":"set","segment":"strip1","pattern":"rainbow","brightness":0.6,"speed":1.0,"params":{"color":[255,0,0]}}
```
- Ping: `{ "cmd": "ping" }` (ESP32 replies on its status topic if implemented).

## Notes
- Change hardcoded Wi-Fi and MQTT credentials in `firmware/esp32_firmware.ino` before sharing/building.
- LED segments and pin mapping are defined near the top of the firmware file; keep `SEGMENTS` and strip lengths in sync.
- The host tools are stateless beyond `led_states.json`; delete it to regenerate defaults.
