import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import requests
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


LED_UI_URL = os.environ.get("LED_UI_URL", "http://localhost:5000/quickmenu")
PORT = int(os.environ.get("PORT", "8888"))
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "change-this-secret")
TOKEN_PATH = Path(os.environ.get("TOKEN_PATH", Path(__file__).with_name("tokens.json")))

SCOPES = [
    "user-read-currently-playing",
    "user-read-playback-state",
    "user-modify-playback-state",
]

app = Flask(__name__)
app.secret_key = SESSION_SECRET


class SpotifyAPI:
    def __init__(self, token_path: Path):
        self.token_path = token_path
        self.token_data: Dict[str, Any] = {}
        self.load_tokens()

    def load_tokens(self) -> None:
        if self.token_path.exists():
            try:
                self.token_data = json.loads(self.token_path.read_text())
            except Exception:
                self.token_data = {}

    def save_tokens(self) -> None:
        self.token_path.write_text(json.dumps(self.token_data))

    @property
    def has_tokens(self) -> bool:
        return bool(self.token_data.get("access_token"))

    def token_expired(self) -> bool:
        return time.time() >= self.token_data.get("expires_at", 0)

    def refresh_access_token(self) -> bool:
        refresh_token = self.token_data.get("refresh_token")
        if not refresh_token:
            return False

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        auth = (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
        try:
            resp = requests.post(
                "https://accounts.spotify.com/api/token",
                data=data,
                auth=auth,
                timeout=10,
            )
        except requests.RequestException:
            return False

        if resp.status_code != 200:
            return False

        payload = resp.json()
        self.token_data["access_token"] = payload["access_token"]
        # Spotify may not return refresh_token on refresh, so keep the old one
        if payload.get("refresh_token"):
            self.token_data["refresh_token"] = payload["refresh_token"]
        self.token_data["expires_at"] = time.time() + payload.get("expires_in", 3600) - 60
        self.save_tokens()
        return True

    def ensure_access_token(self) -> bool:
        if not self.has_tokens:
            return False
        if self.token_expired():
            return self.refresh_access_token()
        return True

    def spotify_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        retry: bool = True,
    ) -> Tuple[bool, Any, int]:
        if not self.ensure_access_token():
            return False, {"error": "not_authenticated"}, 401

        headers = {"Authorization": f"Bearer {self.token_data['access_token']}"}
        url = f"https://api.spotify.com{endpoint}"

        try:
            resp = requests.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=10,
            )
        except requests.RequestException as exc:
            return False, {"error": str(exc)}, 500

        if resp.status_code == 401 and retry and self.refresh_access_token():
            return self.spotify_request(method, endpoint, params, json_body, retry=False)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            return False, {"error": "rate_limited", "retry_after": retry_after}, 429

        if resp.status_code >= 400:
            try:
                data = resp.json()
            except ValueError:
                data = {"error": resp.text}
            return False, data, resp.status_code

        if resp.content:
            try:
                return True, resp.json(), resp.status_code
            except ValueError:
                return True, resp.text, resp.status_code
        return True, None, resp.status_code


spotify_api = SpotifyAPI(TOKEN_PATH)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/led")
def go_to_led():
    return redirect(LED_UI_URL, code=302)


@app.route("/login")
def login():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET or not SPOTIFY_REDIRECT_URI:
        return (
            "Spotify client ID/secret/redirect URI are not configured. "
            "Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI environment variables.",
            500,
        )

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    query = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": state,
        "show_dialog": "false",
    }
    return redirect(f"https://accounts.spotify.com/authorize?{urlencode(query)}")


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        return f"Spotify authorization failed: {error}", 400

    state = request.args.get("state")
    if not state or state != session.get("oauth_state"):
        return "State mismatch during authentication", 400

    code = request.args.get("code")
    if not code:
        return "Missing authorization code", 400

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    }
    auth = (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)

    try:
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data=data,
            auth=auth,
            timeout=10,
        )
    except requests.RequestException as exc:
        return f"Token exchange failed: {exc}", 500

    if resp.status_code != 200:
        return f"Token exchange failed: {resp.text}", 400

    payload = resp.json()
    spotify_api.token_data = {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token", ""),
        "expires_at": time.time() + payload.get("expires_in", 3600) - 60,
    }
    spotify_api.save_tokens()
    session.pop("oauth_state", None)
    return redirect(url_for("spotify_page"))


@app.route("/spotify")
def spotify_page():
    return render_template("spotify.html", authorized=spotify_api.has_tokens)


@app.route("/api/now_playing")
def now_playing():
    ok, data, status = spotify_api.spotify_request("GET", "/v1/me/player/currently-playing")

    if status == 204:
        return jsonify({"playing": False, "message": "Nothing is playing"}), 200

    if not ok:
        return jsonify(data), status

    if not data or not data.get("item"):
        return jsonify({"playing": False, "message": "Nothing is playing"}), 200

    item = data["item"]
    artists = ", ".join(a["name"] for a in item.get("artists", []))
    album_images = item.get("album", {}).get("images", [])
    image_url = album_images[0]["url"] if album_images else None
    progress_ms = data.get("progress_ms", 0)
    duration_ms = item.get("duration_ms", 0)
    device = data.get("device") or {}

    response = {
        "playing": data.get("is_playing", False),
        "title": item.get("name"),
        "artist": artists,
        "album": item.get("album", {}).get("name"),
        "image_url": image_url,
        "progress_ms": progress_ms,
        "duration_ms": duration_ms,
        "device": device.get("name"),
        "volume": device.get("volume_percent"),
        "device_active": device.get("is_active", False),
    }
    return jsonify(response)


@app.route("/api/play_pause", methods=["POST"])
def play_pause():
    # Determine current state to toggle
    ok, data, status = spotify_api.spotify_request("GET", "/v1/me/player")
    if not ok:
        return jsonify(data), status

    is_playing = data.get("is_playing", False)
    endpoint = "/v1/me/player/pause" if is_playing else "/v1/me/player/play"
    ok, data, status = spotify_api.spotify_request("PUT", endpoint)
    http_status = 200 if ok else status
    return jsonify({"ok": ok, "detail": data}), http_status


@app.route("/api/next", methods=["POST"])
def next_track():
    ok, data, status = spotify_api.spotify_request("POST", "/v1/me/player/next")
    http_status = 200 if ok else status
    return jsonify({"ok": ok, "detail": data}), http_status


@app.route("/api/previous", methods=["POST"])
def previous_track():
    ok, data, status = spotify_api.spotify_request("POST", "/v1/me/player/previous")
    http_status = 200 if ok else status
    return jsonify({"ok": ok, "detail": data}), http_status


@app.route("/api/volume", methods=["POST"])
def change_volume():
    body = request.get_json(silent=True) or {}
    delta = body.get("delta")
    if delta is None:
        return jsonify({"error": "Missing delta"}), 400

    ok, data, status = spotify_api.spotify_request("GET", "/v1/me/player")
    if not ok:
        return jsonify(data), status

    device = data.get("device") or {}
    current_volume = device.get("volume_percent")
    if current_volume is None:
        return jsonify({"error": "No active device or volume unavailable"}), 404

    new_volume = max(0, min(100, current_volume + int(delta)))
    params = {"volume_percent": new_volume}
    ok, data, status = spotify_api.spotify_request("PUT", "/v1/me/player/volume", params=params)
    http_status = 200 if ok else status
    return jsonify({"ok": ok, "detail": data, "volume": new_volume}), http_status


@app.route("/api/resume", methods=["POST"])
def resume_playback():
    ok, data, status = spotify_api.spotify_request("PUT", "/v1/me/player/play")
    http_status = 200 if ok else status
    return jsonify({"ok": ok, "detail": data}), http_status


@app.route("/api/pause", methods=["POST"])
def pause_playback():
    ok, data, status = spotify_api.spotify_request("PUT", "/v1/me/player/pause")
    http_status = 200 if ok else status
    return jsonify({"ok": ok, "detail": data}), http_status


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
