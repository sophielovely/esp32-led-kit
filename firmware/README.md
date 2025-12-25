# ESP32 LED Engine (S3 N8R2)

This sketch makes the ESP32 the "engine" that renders LED patterns locally while the Raspberry Pi acts as the "director" sending tiny JSON commands over MQTT. OTA keeps firmware updates coming from the Pi without plugging in USB.

## Features
- MQTT JSON control (topic `led/command`, matches `esp32_led_control.py` and web UI).
- Patterns: `solid`, `rainbow`, `sine`, `wind_meter` (others easy to add).
- Parameters: `brightness`, `speed`, plus per-pattern params like `color`, `wave_shape`, `wind_mph`.
- ArduinoOTA for cable-free reflashing from the Pi.

## Quick build/flash from the Pi
1. Install Arduino CLI once:
   ```bash
   arduino-cli config init
   arduino-cli core update-index
   arduino-cli core install esp32:esp32
   arduino-cli lib install "ArduinoJson" "Adafruit NeoPixel" "PubSubClient"
   ```
2. Edit Wi-Fi + LED config in `esp32_firmware.ino` (SSID, PASS) and set `MQTT_HOST` (e.g., your Pi AP IP if running hostapd/dnsmasq).
3. USB flash the first time (substitute your serial port):
   ```bash
   arduino-cli compile --fqbn esp32:esp32:esp32s3 firmware/esp32_firmware
   arduino-cli upload --fqbn esp32:esp32:esp32s3 -p /dev/ttyACM0 firmware/esp32_firmware
   ```
4. Later OTA updates from the Pi (ESP32 must be on Wi-Fi):
   ```bash
   arduino-cli upload --fqbn esp32:esp32:esp32s3 --port 192.168.1.150 --upload-port 3232 firmware/esp32_firmware
   ```
   (Replace IP with your ESP32 address; OTA port defaults to 3232.)

## MQTT protocol (Pi -> ESP32)
Publish a single JSON object to the command topic (default `led/command`):
- Set pattern + params:
  ```json
  {"cmd":"set","pattern":"rainbow","brightness":0.6,"speed":1.2,"params":{"color":[255,64,0],"wave_shape":"sine"}}
  ```
- Ping:
  ```json
  {"cmd":"ping"}
  ```

The Pi helper `esp32_led_control.py` wraps these for quick CLI use; it only publishes and does not wait for a reply. The ESP32 publishes `{"status":"online"}` and `{"pong":true}` on the status topic (`led/status`).

## Pattern notes
- `solid`: uses `params.color` (RGB array) or defaults to teal.
- `rainbow`: continuous hue wheel; `speed` controls flow rate.
- `sine`: brightness sine wave; optional `params.wave_shape` (`sine`, `square`, `triangle`).
- `wind_meter`: intended for Pi wind data; lights proportionally to `params.wind_mph`.

Add new patterns by editing `render_pattern()` in `esp32_firmware.ino` and teaching the Pi to request it.
