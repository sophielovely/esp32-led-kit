(function () {
  const authorized = window.SPOTIFY_AUTHORIZED === true || window.SPOTIFY_AUTHORIZED === "true";
  if (!authorized) return;

  const albumArt = document.getElementById("albumArt");
  const artPlaceholder = document.getElementById("artPlaceholder");
  const trackTitle = document.getElementById("trackTitle");
  const trackArtist = document.getElementById("trackArtist");
  const deviceStatus = document.getElementById("deviceStatus");
  const helperText = document.getElementById("helperText");
  const playPauseBtn = document.getElementById("playPauseBtn");

  const POLL_MS = 2000;

  function setHelper(message) {
    helperText.textContent = message || "";
  }

  function setArt(url) {
    if (url) {
      albumArt.src = url;
      albumArt.style.display = "block";
      artPlaceholder.style.display = "none";
    } else {
      albumArt.style.display = "none";
      artPlaceholder.style.display = "grid";
    }
  }

  function updateUI(data) {
    if (!data.playing) {
      trackTitle.textContent = data.message || "Nothing is playing";
      trackArtist.textContent = "";
      playPauseBtn.textContent = "▶";
      setArt(null);
      deviceStatus.textContent = data.device || "No active device";
      return;
    }

    trackTitle.textContent = data.title || "Unknown track";
    trackArtist.textContent = data.artist || "";
    playPauseBtn.textContent = data.playing ? "⏸" : "▶";
    setArt(data.image_url);
    deviceStatus.textContent = data.device || "Active device";
  }

  async function fetchJson(path, options) {
    const resp = await fetch(path, options);
    const contentType = resp.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await resp.json() : {};
    return { ok: resp.ok, status: resp.status, body };
  }

  async function refresh() {
    try {
      const { ok, status, body } = await fetchJson("/api/now_playing");
      if (!ok) {
        if (status === 401) {
          setHelper("Not authorized. Tap Sign in to Spotify.");
        } else if (status === 429) {
          setHelper(`Rate limited. Retry after ${body.retry_after || 1}s`);
        } else {
          setHelper(body.error || "Unable to reach Spotify");
        }
        return;
      }
      setHelper("");
      updateUI(body);
    } catch (err) {
      setHelper("Network error");
    }
  }

  async function sendCommand(path, body) {
    setHelper("");
    const { ok, status, body: respBody } = await fetchJson(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!ok) {
      if (status === 401) {
        setHelper("Re-link Spotify (Sign in).");
      } else if (status === 429) {
        setHelper(`Rate limited. Retry after ${respBody.retry_after || 1}s`);
      } else {
        setHelper(respBody.error || "Action failed");
      }
    }
    refresh();
  }

  document.getElementById("prevBtn").addEventListener("click", () => sendCommand("/api/previous"));
  document.getElementById("nextBtn").addEventListener("click", () => sendCommand("/api/next"));
  playPauseBtn.addEventListener("click", () => sendCommand("/api/play_pause"));
  document.getElementById("volDown").addEventListener("click", () => sendCommand("/api/volume", { delta: -10 }));
  document.getElementById("volUp").addEventListener("click", () => sendCommand("/api/volume", { delta: 10 }));

  refresh();
  setInterval(refresh, POLL_MS);
})();
