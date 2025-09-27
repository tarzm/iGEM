async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts));
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

async function seedHistory(minutes) {
  try {
    const res = await fetch(`/api/history?minutes=${encodeURIComponent(minutes)}`);
    if (!res.ok) return;
    const payload = await res.json();
    const rows = payload.data || [];
    // Reset arrays
    tempTimes.length = 0; tempValues.length = 0;
    phTimes.length = 0; phValues.length = 0;
    // Only keep last 30 minutes in case backend returned more
    const nowMs = Date.now();
    const cutoff = nowMs - windowMs;
    let lastKept = 0;
    for (const r of rows) {
      const ts = typeof r.ts === 'number' ? r.ts : Date.parse(r.timestamp);
      if (ts >= cutoff) {
        if (ts - lastKept >= plotIntervalMs) {
          tempTimes.push(ts);
          tempValues.push(r.temperature_c != null ? r.temperature_c : null);
          phTimes.push(ts);
          phValues.push(r.ph != null ? r.ph : null);
          lastKept = ts;
        }
      }
    }
    // Snap lastBucket to last historical bucket to honor 10s spacing
    if (tempTimes.length) {
      lastBucket = Math.floor(tempTimes[tempTimes.length - 1] / plotIntervalMs);
    }
    // Render datasets
    const nowSec = Date.now() / 1000;
    if (tempChart) {
      tempChart.data.datasets[0].data = tempTimes.map((t, i) => ({ x: (t / 1000) - nowSec, y: tempValues[i] }));
      tempChart.update('none');
    }
    if (phChart) {
      phChart.data.datasets[0].data = phTimes.map((t, i) => ({ x: (t / 1000) - nowSec, y: phValues[i] }));
      phChart.update('none');
    }
  } catch {}
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

  setText('temp-c', tC != null ? tC.toFixed(2) : '--');
  setText('temp-f', tF != null ? tF.toFixed(2) : '--');
  setText('ph', pH != null ? pH.toFixed(2) : '--');
  setText('fan-note', fan ? 'ON' : 'OFF');

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

  // Push to charts
  appendToCharts({ tC, pH });
}

async function refresh() {
  try {
    const data = await fetchJSON('/api/status');
    updateUI(data);
  } catch (e) {
    console.error('Failed to fetch status', e);
  }
}

function init() {
  setupCharts();
  // Load 30 min history first, then start polling
  seedHistory(30).then(() => {
    refresh();
    setInterval(refresh, 2000);
  });

  // Fullscreen toggle
  const fsBtn = document.getElementById('btn-fullscreen');
  if (fsBtn) {
    fsBtn.addEventListener('click', toggleFullscreen);
    document.addEventListener('fullscreenchange', updateFullscreenButton);
    updateFullscreenButton();
  }
}

window.addEventListener('DOMContentLoaded', init);

// ==== Charts ====
let tempChart = null;
let phChart = null;
const windowMs = 30 * 60 * 1000; // 30 minutes
// Parallel arrays for timestamps (ms since epoch) and values
const tempTimes = [];
const phTimes = [];
const tempValues = [];
const phValues = [];
// Plotting cadence (downsample to avoid clutter): one point every 10 seconds
const plotIntervalMs = 10 * 1000;
let lastBucket = null; // integer bucket index = floor(ts / plotIntervalMs)

function setupCharts() {
  const ctxT = document.getElementById('tempChart');
  const ctxP = document.getElementById('phChart');

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: { display: false },
      tooltip: { mode: 'nearest', intersect: false }
    },
    scales: {
      x: {
        type: 'linear',
        min: -1800, // -30 min in seconds
        max: 0,
        ticks: {
          maxRotation: 0,
          autoSkip: false,
          count: 4,
          callback: (value) => formatRelativeTick(value)
        },
        grid: { display: false },
        title: { display: true, text: 'time' }
      },
      y: {
        grid: { color: 'rgba(0,0,0,0.06)' }
      }
    }
  };

  tempChart = new Chart(ctxT, {
    type: 'line',
    data: {
      datasets: [{
        label: '°C',
        data: [], // {x: seconds relative to now (negative..0), y: temp}
        borderColor: '#0b7a3c',
        backgroundColor: 'rgba(11,122,60,0.15)',
        tension: 0.25,
        pointRadius: 0,
        fill: true
      }]
    },
    options: {
      ...commonOptions,
      scales: {
        ...commonOptions.scales,
        y: { ...commonOptions.scales.y, min: 10, max: 40, title: { display: true, text: '°C' } }
      }
    }
  });

  phChart = new Chart(ctxP, {
    type: 'line',
    data: {
      datasets: [{
        label: 'pH',
        data: [], // {x: seconds relative to now (negative..0), y: pH}
        borderColor: '#1a9850',
        backgroundColor: 'rgba(26,152,80,0.15)',
        tension: 0.25,
        pointRadius: 0,
        fill: true
      }]
    },
    options: {
      ...commonOptions,
      scales: {
        ...commonOptions.scales,
        y: { ...commonOptions.scales.y, min: 5, max: 9, title: { display: true, text: 'pH' } }
      }
    }
  });
}

function appendToCharts({ tC, pH }) {
  const now = new Date();
  const nowMs = now.getTime();
  const cutoff = nowMs - windowMs;
  // Append new samples
  const bucket = Math.floor(nowMs / plotIntervalMs);
  if (lastBucket !== null && bucket === lastBucket) {
    // Still in the same 10s bucket; skip plotting
    return;
  }
  lastBucket = bucket;

  // Temperature chart
  if (tempChart) {
    tempTimes.push(nowMs);
    tempValues.push(tC != null ? tC : null);
    // Trim to last 30 minutes
    while (tempTimes.length && tempTimes[0] < cutoff) {
      tempTimes.shift();
      tempValues.shift();
    }
    // Recompute dataset as {x,y} with x in seconds relative to now
    tempChart.data.datasets[0].data = tempTimes.map((t, i) => ({ x: (t - nowMs) / 1000, y: tempValues[i] }));
    // Ensure x-axis reflects the current window [-1800..0]
    tempChart.options.scales.x.min = -windowMs / 1000;
    tempChart.options.scales.x.max = 0;
    tempChart.update('none');
  }

  // pH chart
  if (phChart) {
    phTimes.push(nowMs);
    phValues.push(pH != null ? pH : null);
    // Trim to last 30 minutes
    while (phTimes.length && phTimes[0] < cutoff) {
      phTimes.shift();
      phValues.shift();
    }
    // Recompute dataset as {x,y}
    phChart.data.datasets[0].data = phTimes.map((t, i) => ({ x: (t - nowMs) / 1000, y: phValues[i] }));
    phChart.options.scales.x.min = -windowMs / 1000;
    phChart.options.scales.x.max = 0;
    phChart.update('none');
  }
}

function formatRelativeTick(value) {
  const v = Math.round(value);
  if (v === 0) return 'now';
  const neg = -v;
  if (neg < 60) {
    // Round to nearest 5 seconds for readability
    const s = Math.round(neg / 5) * 5;
    return `-${s} s`;
  }
  const m = Math.round(neg / 60);
  return `-${m} min`;
}

// ==== Fullscreen helpers ====
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen().catch(() => {});
  }
}

function updateFullscreenButton() {
  const fsBtn = document.getElementById('btn-fullscreen');
  if (!fsBtn) return;
  const inFs = !!document.fullscreenElement;
  fsBtn.textContent = inFs ? 'Exit Fullscreen' : 'Fullscreen';
}
