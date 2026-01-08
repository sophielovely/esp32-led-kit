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
  scrollbar-width: none;
  -ms-overflow-style: none;
}
body::-webkit-scrollbar { display: none; }
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
        <a href=\"/quickmenu\" style=\"text-decoration:none;\">
          <button class=\"btn-secondary\" style=\"padding:10px 12px;\">Open Quick Menu</button>
        </a>
        <a href=\"/weather\" style=\"text-decoration:none;\">
          <button class=\"btn-secondary\" style=\"padding:10px 12px; background:#e0f2ff;\">Weather</button>
        </a>
        <button class=\"btn-secondary\" style=\"padding:10px 12px; background:#ffd1d1;\" onclick=\"closeChromium()\">Close Chromium</button>
        <div class=\"badge\" id=\"svc-badge\"><span class=\"status-dot\" id=\"svc-dot\"></span><span id=\"svc-text\">Service: …</span></div>
        <div class=\"badge\" id=\"esp-badge\"><span class=\"status-dot\" id=\"esp-dot\" style=\"background:#f2a900; box-shadow:0 0 10px #f2a900;\"></span><span id=\"esp-text\">ESP: …</span></div>
        <div class=\"badge\" id=\"esp2-badge\"><span class=\"status-dot\" id=\"esp2-dot\" style=\"background:#f2a900; box-shadow:0 0 10px #f2a900;\"></span><span id=\"esp2-text\">ESP2: …</span></div>
        <div class=\"badge\" id=\"esp3-badge\"><span class=\"status-dot\" id=\"esp3-dot\" style=\"background:#f2a900; box-shadow:0 0 10px #f2a900;\"></span><span id=\"esp3-text\">ESP3: …</span></div>
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
    <div class=\"card\" style=\"margin-top:12px; background:#f9fbff;\">
      <div style=\"display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;\">
        <h3 style=\"margin:0;\">Camming lights (ESP32U)</h3>
        <div class=\"pill\" style=\"background:#fff;\">Pins 33 · 32 · 300 LEDs each</div>
      </div>
      <p style=\"margin:6px 0 10px; color:var(--muted);\">Dedicated controls for the ESP32U. Brightness and presets are independent from the other strips.</p>
      <div class=\"grid\" style=\"grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));\">
        <div class=\"field\">
          <label>Brightness</label>
          <div class=\"range\">
            <input id=\"esp3_brightness\" type=\"range\" min=\"0\" max=\"255\" value=\"200\" oninput=\"esp3BOut.textContent=this.value; scheduleEsp3Apply();\">
            <output id=\"esp3BOut\">200</output>
          </div>
        </div>
      </div>
      <div class=\"grid\" style=\"margin-top:10px; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));\">
        <button onclick=\"esp3White()\">White</button>
        <button class=\"btn-secondary\" onclick=\"esp3Rainbow()\">Rainbow</button>
        <button class=\"btn-secondary\" style=\"background:#ffe3ff;\" onclick=\"esp3Hills()\">Rainbow hills</button>
        <button class=\"btn-secondary\" style=\"background:#ffd1d1;\" onclick=\"esp3Off()\">Off</button>
      </div>
    </div>
    <div class=\"card\" style=\"margin-top:12px; background:#f6fff8;\">
      <h3 style=\"margin:0 0 8px;\">Camming presets</h3>
      <div class=\"grid\" style=\"grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); align-items:end;\">
        <div class=\"field\">
          <label>Saved camming states</label>
          <select id=\"esp3-state-select\"></select>
        </div>
        <input id=\"esp3-state-name\" type=\"text\" placeholder=\"Name (e.g. soft white)\" style=\"padding:10px 12px; border-radius:10px; border:1px solid var(--border); font-size:14px; min-width:160px;\">
        <button onclick=\"saveEsp3State()\">Save current</button>
        <button class=\"btn-secondary\" onclick=\"applyEsp3State()\">Apply</button>
        <button class=\"btn-secondary\" onclick=\"setDefaultEsp3State()\">Set default</button>
        <button class=\"btn-secondary\" style=\"background:#ffd1d1;\" onclick=\"deleteEsp3State()\">Delete</button>
      </div>
      <div id=\"esp3-default-label\" class=\"pill\" style=\"margin-top:6px;\">Default: none</div>
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

async function loadEsp3State() {
  try {
    const res = await fetch('/api/esp3/state');
    const data = await res.json();
    if (data && data.state) {
      esp3State = Object.assign(esp3State, data.state || {});
      if (esp3State.last_pattern) esp3LastPattern = esp3State.last_pattern;
      if (esp3State.brightness !== undefined) {
        document.getElementById('esp3_brightness').value = esp3State.brightness;
        document.getElementById('esp3BOut').textContent = esp3State.brightness;
      }
    }
  } catch (e) {
    // ignore
  }
}

async function sendEsp3(pattern, opts = {}) {
  esp3LastPattern = pattern || esp3LastPattern || 'white';
  const body = {
    pattern: esp3LastPattern,
    brightness: parseFloat(opts.brightness ?? document.getElementById('esp3_brightness').value ?? esp3State.brightness ?? 200),
    target: opts.target || 'both',
  };
  await fetch('/api/esp3/set', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
}
function esp3White() { sendEsp3('white'); }
function esp3Rainbow() { sendEsp3('rainbow'); }
function esp3Hills() { sendEsp3('rainbow_hills'); }
function esp3Off() {
  esp3ApplyTimer && clearTimeout(esp3ApplyTimer);
  document.getElementById('esp3_brightness').value = 0;
  document.getElementById('esp3BOut').textContent = 0;
  sendEsp3(esp3LastPattern || 'white', {brightness: 0, target: 'both'});
}
// Debounced apply when sliders move so brightness takes effect.
let esp3ApplyTimer = null;
function scheduleEsp3Apply() {
  if (esp3ApplyTimer) clearTimeout(esp3ApplyTimer);
  esp3ApplyTimer = setTimeout(() => {
    sendEsp3(esp3LastPattern || 'white');
  }, 120);
}

async function lightsOff() {
  await fetch('/api/set-all', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({brightness: 0})});
  await fetch('/api/esp3/set', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({brightness: 0, pattern: esp3LastPattern || 'white', target:'both'})});
  document.getElementById('gbrightness').value = 0;
  document.getElementById('gbOut').textContent = 0;
  refreshState();
}

async function closeChromium() {
  try {
    const res = await fetch('/api/close-chromium', {method:'POST'});
    const data = await res.json();
    const msg = data && data.killed ? 'Chromium close requested.' : 'No Chromium processes were running.';
    alert(msg);
  } catch (e) {
    alert('Close Chromium failed.');
  }
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
  await fetch('/api/esp3/set', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({pattern: esp3LastPattern || 'white', brightness: esp3State.brightness || 200, target:'both'})});
  document.getElementById('gbrightness').value = 180;
  document.getElementById('gbOut').textContent = 180;
  refreshState();
}
const stateCache = {};
let defaultStateName = null;
const liveState = {};
const gradientPalettes = {{ gradients|tojson }};
const esp2Ip = "{{ esp2_default_ip }}";
const esp3Ip = "{{ esp3_default_ip }}";
let esp3State = {brightness: 200, white_balance: 4500, last_pattern: 'white', target:'both'};
let esp3LastPattern = 'white';
const esp3StateCache = {};
let esp3DefaultStateName = null;

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

async function refreshEsp3StatesList() {
  try {
    const res = await fetch('/api/esp3/states');
    const data = await res.json();
    const sel = document.getElementById('esp3-state-select');
    sel.innerHTML = '';
    Object.keys(esp3StateCache).forEach((k) => delete esp3StateCache[k]);
    (data.states || []).forEach((s) => {
      esp3StateCache[s.name] = s.data;
      const opt = document.createElement('option');
      opt.value = s.name;
      opt.textContent = s.name;
      sel.appendChild(opt);
    });
    esp3DefaultStateName = data.default || null;
    const label = document.getElementById('esp3-default-label');
    if (label) label.textContent = `Default: ${esp3DefaultStateName || 'none'}`;
    if (esp3DefaultStateName && sel.options.length) {
      sel.value = esp3DefaultStateName;
    }
  } catch (e) {
    // ignore
  }
}

async function saveEsp3State() {
  const name = (document.getElementById('esp3-state-name').value || '').trim();
  if (!name) return;
  await fetch('/api/esp3/state/save', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
  await refreshEsp3StatesList();
  document.getElementById('esp3-state-select').value = name;
}

async function applyEsp3State() {
  const sel = document.getElementById('esp3-state-select');
  const name = sel.value;
  if (!name) return;
  await fetch('/api/esp3/state/apply', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
  await loadEsp3State();
}

async function setDefaultEsp3State() {
  const sel = document.getElementById('esp3-state-select');
  const name = sel.value;
  if (!name) return;
  await fetch('/api/esp3/state/default', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
  esp3DefaultStateName = name;
  const label = document.getElementById('esp3-default-label');
  if (label) label.textContent = `Default: ${esp3DefaultStateName}`;
  await applyEsp3State();
}

async function deleteEsp3State() {
  const sel = document.getElementById('esp3-state-select');
  const name = sel.value;
  if (!name) return;
  const sure = window.confirm(`Delete camming preset "${name}"?`);
  if (!sure) return;
  await fetch('/api/esp3/state/delete', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
  await refreshEsp3StatesList();
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
loadEsp3State();
refreshEsp3StatesList();

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
async function refreshEsp3() {
  const dot = document.getElementById('esp3-dot');
  const text = document.getElementById('esp3-text');
  if (!dot || !text) return;
  try {
    const res = await fetch(`/api/esp-status?ip=${esp3Ip}`);
    const data = await res.json();
    if (data.reachable) {
      text.textContent = `ESP3 ${data.ip}: online`;
      dot.style.background = '#00c853';
      dot.style.boxShadow = '0 0 12px #00c853';
    } else {
      text.textContent = `ESP3 ${data.ip}: offline?`;
      dot.style.background = '#ff7f7f';
      dot.style.boxShadow = '0 0 12px #ff7f7f';
    }
  } catch (e) {
    text.textContent = 'ESP3: unknown';
    dot.style.background = '#ff7f7f';
    dot.style.boxShadow = '0 0 12px #ff7f7f';
  }
}
refreshEsp3();
setInterval(refreshEsp3, 7000);

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
