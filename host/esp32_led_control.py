"""
Lightweight ESP32 LED pattern controller from the Pi (MQTT).

- Publishes JSON commands to an MQTT broker the ESP32 subscribes to.
- CLI examples:
    python3 esp32_led_control.py --host 127.0.0.1 set --pattern rainbow --speed 1.2 --brightness 0.7
    python3 esp32_led_control.py --host 127.0.0.1 set --pattern solid --color 255 64 0

Expected firmware protocol on the ESP32 (see esp32_firmware/esp32_firmware.ino):
{"cmd":"set","pattern":"rainbow","brightness":0.6,"speed":1.0,"params":{"color":[255,0,0]}}
{"cmd":"ping"}
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any, Dict, List, Optional, Sequence

import paho.mqtt.client as mqtt

DEFAULT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DEFAULT_HOST = os.getenv("MQTT_HOST")
DEFAULT_TOPIC = os.getenv("MQTT_CMD_TOPIC", "led/command")
DEFAULT_BRIGHTNESS = 255.0


def _publish(
    host: str,
    port: int,
    topic: str,
    payload: Dict[str, Any],
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    client = mqtt.Client(client_id=f"led-cli-{int(time.time()*1000)}")
    if username:
        client.username_pw_set(username, password)
    client.connect(host, port, keepalive=15)
    client.loop_start()
    try:
        client.publish(topic, json.dumps(payload), qos=0, retain=False)
        # give the network thread a beat to flush
        time.sleep(0.1)
    finally:
        client.loop_stop()
        client.disconnect()


def set_pattern(
    host: str,
    *,
    port: int = DEFAULT_PORT,
    topic: str = DEFAULT_TOPIC,
    segment: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    pattern: str,
    brightness: float = DEFAULT_BRIGHTNESS,
    speed: float = 1.0,
    color: Optional[Sequence[int]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    params: Dict[str, Any] = {}
    if color is not None:
        params["color"] = [int(x) for x in color]
    if extra:
        params.update(extra)
    payload = {
        "cmd": "set",
        "pattern": pattern,
        "brightness": float(brightness),
        "speed": float(speed),
        "params": params,
    }
    if segment:
        payload["segment"] = segment
    _publish(host, port, topic, payload, username=username, password=password)


def ping(
    host: str,
    *,
    port: int = DEFAULT_PORT,
    topic: str = DEFAULT_TOPIC,
    segment: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    payload: Dict[str, Any] = {"cmd": "ping"}
    if segment:
        payload["segment"] = segment
    _publish(host, port, topic, payload, username=username, password=password)


def parse_color(values: List[str]) -> List[int]:
    if len(values) != 3:
        raise argparse.ArgumentTypeError("color expects 3 numbers (r g b)")
    rgb = [max(0, min(255, int(v))) for v in values]
    return rgb


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Send LED pattern commands to an ESP32 over MQTT")
    parser.add_argument("--host", default=DEFAULT_HOST, required=DEFAULT_HOST is None, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="MQTT command topic (default led/command)")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--segment", help="Segment name (e.g., strip1, seg250_323, seg330_400)")

    sub = parser.add_subparsers(dest="cmd", required=True)

    set_p = sub.add_parser("set", help="Set pattern and parameters")
    set_p.add_argument("--pattern", required=True, help="Pattern name on the ESP32")
    set_p.add_argument("--brightness", type=float, default=1.0)
    set_p.add_argument("--speed", type=float, default=1.0)
    set_p.add_argument("--color", nargs=3, metavar=("R", "G", "B"), help="RGB triplet 0-255")
    set_p.add_argument("--wave-shape", dest="wave_shape", help="Optional wave shape param")

    sub.add_parser("ping", help="Send ping command")

    args = parser.parse_args(argv)

    if args.cmd == "set":
        color = parse_color(args.color) if args.color else None
        extra: Dict[str, Any] = {}
        if args.wave_shape:
            extra["wave_shape"] = args.wave_shape
        set_pattern(
            args.host,
            port=args.port,
            topic=args.topic,
            segment=args.segment,
            username=args.username,
            password=args.password,
            pattern=args.pattern,
            brightness=args.brightness,
            speed=args.speed,
            color=color,
            extra=extra,
        )
    elif args.cmd == "ping":
        ping(
            args.host,
            port=args.port,
            topic=args.topic,
            segment=args.segment,
            username=args.username,
            password=args.password,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
