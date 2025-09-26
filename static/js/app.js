async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts));
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setCardState(cardId, state) {
  const card = document.getElementById(cardId);
  if (!card) return;
  card.classList.remove('good', 'warn', 'bad');
  card.classList.add(state);
}

function updateUI(data) {
  const tC = data.temperature_c;
  const tF = data.temperature_f;
  const pH = data.ph;
  const fan = data.fan_running;
  const status = data.algae_status || { emoji: '❓', message: 'Unknown' };

  setText('temp-c', tC != null ? tC.toFixed(2) : '--');
  setText('temp-f', tF != null ? tF.toFixed(2) : '--');
  setText('ph', pH != null ? pH.toFixed(2) : '--');
  setText('fan-status', fan ? 'ON' : 'OFF');

  setText('status-emoji', status.emoji);
  setText('status-message', status.message);

  document.getElementById('algae-emoji').textContent = status.emoji;
  document.getElementById('algae-title').textContent = status.status ? status.status.toUpperCase() : 'STATUS';
  document.getElementById('algae-desc').textContent = status.message || '';

  // Color coding
  if (tC != null) {
    if (tC >= 20 && tC <= 30) setCardState('card-temp', 'good');
    else if (tC >= 18 && tC <= 32) setCardState('card-temp', 'warn');
    else setCardState('card-temp', 'bad');
  }
  if (pH != null) {
    if (pH >= 6.5 && pH <= 8.5) setCardState('card-ph', 'good');
    else if (pH >= 6.0 && pH <= 9.0) setCardState('card-ph', 'warn');
    else setCardState('card-ph', 'bad');
  }

  setCardState('card-fan', fan ? 'good' : 'warn');
}

async function refresh() {
  try {
    const data = await fetchJSON('/api/status');
    updateUI(data);
  } catch (e) {
    console.error('Failed to fetch status', e);
  }
}

async function loadConfig() {
  try {
    const cfg = await fetchJSON('/api/config');
    document.getElementById('threshold').value = cfg.fan_temp_threshold;
  } catch (e) {
    console.error('Failed to load config', e);
  }
}

async function setFan(on) {
  try {
    await fetchJSON('/api/fan', { method: 'POST', body: JSON.stringify({ action: on ? 'start' : 'stop' }) });
    await refresh();
  } catch (e) {
    console.error('Failed to set fan', e);
  }
}

async function saveThreshold() {
  const v = parseFloat(document.getElementById('threshold').value);
  if (Number.isNaN(v)) return;
  try {
    await fetchJSON('/api/config', { method: 'POST', body: JSON.stringify({ fan_temp_threshold: v }) });
    await refresh();
  } catch (e) {
    console.error('Failed to save threshold', e);
  }
}

function init() {
  document.getElementById('btn-fan-on').addEventListener('click', () => setFan(true));
  document.getElementById('btn-fan-off').addEventListener('click', () => setFan(false));
  document.getElementById('btn-save-threshold').addEventListener('click', saveThreshold);

  loadConfig();
  refresh();
  setInterval(refresh, 2000);
}

window.addEventListener('DOMContentLoaded', init);
