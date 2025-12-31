# ESP32U Camming Lights Firmware

Firmware for the dedicated ESP32U that drives two 300-LED strips on GPIO33 and GPIO32 (matrix use removed; plain strip control only).

## Features
- MQTT control on topic `esp32u/command`.
- Patterns: `white`, `rainbow`, `rainbow_hills` (soft “hills” of mini-rainbows).
- Brightness 0-255 applied per pattern.
- OTA enabled (ArduinoOTA hostname `esp32u-camming`).
- Wi-Fi locked to your AP SSID with BSSID/channel fallback (edit in the sketch).

## Hardware
- Strip A: GPIO33, 300 LEDs.
- Strip B: GPIO32, 300 LEDs.
- ESP32 (classic) using Adafruit_NeoPixel (GRB, 800 kHz).

## Build / Flash
```bash
arduino-cli lib install "ArduinoJson" "Adafruit NeoPixel" "PubSubClient"
arduino-cli compile --fqbn esp32:esp32:esp32 esp32u_camming
# First time over USB (replace port):
arduino-cli upload --fqbn esp32:esp32:esp32 -p /dev/ttyUSB0 esp32u_camming
# OTA later (board on Wi-Fi, adjust IP):
python ~/.arduino15/packages/esp32/hardware/esp32/3.3.4/tools/espota.py \
  -i 10.42.0.173 -p 3232 -f /tmp/esp3_ota/esp32u_camming.ino.bin
```

## MQTT Payloads
Publish JSON to `esp32u/command`:
- White:
```json
{"cmd":"set","pattern":"white","brightness":200,"white_balance":4500,"color":[255,217,187]}
```
- Rainbow:
```json
{"cmd":"set","pattern":"rainbow","brightness":220}
```
- Rainbow hills:
```json
{"cmd":"set","pattern":"rainbow_hills","brightness":220}
```

## Status
- Status topic: `esp32u/status` (`{"status":"online","ip":"...","rssi":...}` every ~5s).

