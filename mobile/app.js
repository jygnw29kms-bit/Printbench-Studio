const qs = (id) => document.getElementById(id);

const state = {
  endpoint: localStorage.getItem('printbenchEndpoint') || `${location.protocol}//${location.hostname}:8765`,
  printer: null,
  socket: null,
  cameraOn: false,
  retryTimer: null,
};

const mockPrinter = {
  id: '135er-melti',
  name: '135er-Melti',
  online: true,
  job: { name: 'PRINTBENCH Testteil.3mf', progress: 37, remainingMinutes: 84, status: 'printing' },
  temperatures: { nozzle: 220, nozzleTarget: 220, bed: 58, bedTarget: 60, chamber: 34 },
  speed: { label: 'Standard', percent: 100 },
  ams: {
    label: 'AMS 2 Pro', status: 'Bereit', slots: [
      { slot: 1, material: 'PETG', color: '#242424', remaining: 73 },
      { slot: 2, material: 'PETG', color: '#f3f4f6', remaining: 41 },
      { slot: 3, material: 'PLA', color: '#e74c3c', remaining: 88 },
      { slot: 4, material: 'Leer', color: '#56606d', remaining: 0 },
    ]
  }
};

function render(data) {
  state.printer = data;
  qs('printerName').textContent = data.name || 'PRINTBENCH Drucker';
  const conn = qs('connectionState');
  conn.classList.toggle('online', !!data.online);
  conn.classList.toggle('offline', !data.online);
  conn.querySelector('span:last-child').textContent = data.online ? 'LAN verbunden' : 'Offline';

  const job = data.job || {};
  const progress = Number(job.progress || 0);
  qs('jobName').textContent = job.name || 'Kein aktiver Druck';
  qs('progressBar').style.width = `${Math.max(0, Math.min(100, progress))}%`;
  qs('progressText').textContent = `${progress} %`;
  qs('remainingTime').textContent = job.remainingMinutes ? `${formatMinutes(job.remainingMinutes)} verbleibend` : (job.status === 'idle' ? 'Bereit' : '–');

  const t = data.temperatures || {};
  qs('nozzleTemp').textContent = temp(t.nozzle);
  qs('nozzleTarget').textContent = `Soll ${temp(t.nozzleTarget)}`;
  qs('bedTemp').textContent = temp(t.bed);
  qs('bedTarget').textContent = `Soll ${temp(t.bedTarget)}`;
  qs('chamberTemp').textContent = temp(t.chamber);
  qs('speedLevel').textContent = data.speed?.label || '–';
  qs('speedPercent').textContent = `${data.speed?.percent ?? '–'} %`;

  qs('amsStatus').textContent = data.ams?.status || '–';
  qs('amsSlots').innerHTML = (data.ams?.slots || []).map(slot => `
    <div class="ams-slot">
      <div class="ams-color" style="background:${escapeCssColor(slot.color)}"></div>
      <strong>${escapeHtml(slot.material || 'Leer')}</strong>
      <small>Slot ${slot.slot} · ${Number(slot.remaining || 0)} %</small>
    </div>`).join('');
}

function temp(value) {
  return Number.isFinite(Number(value)) ? `${Math.round(Number(value))}°` : '--°';
}

function formatMinutes(minutes) {
  const m = Math.max(0, Number(minutes) || 0);
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return h ? `${h} h ${rest} min` : `${rest} min`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function escapeCssColor(value) {
  return /^#[0-9a-f]{3,8}$/i.test(String(value)) ? String(value) : '#56606d';
}

async function command(action, payload = {}) {
  try {
    const response = await fetch(`${state.endpoint}/api/v1/printers/${encodeURIComponent(state.printer?.id || 'default')}/commands`, {
      method: 'POST',
      headers: {'content-type':'application/json'},
      body: JSON.stringify({ action, ...payload }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
  } catch (error) {
    console.warn(`PRINTBENCH command ${action} failed`, error);
  }
}

function connect() {
  clearTimeout(state.retryTimer);
  const wsUrl = state.endpoint.replace(/^http/, 'ws') + '/api/v1/events';
  try {
    state.socket = new WebSocket(wsUrl);
    state.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'printer.snapshot' || message.type === 'printer.update') render(message.data);
      } catch (error) { console.warn('Invalid PRINTBENCH event', error); }
    };
    state.socket.onopen = hydrate;
    state.socket.onclose = () => { markDisconnected(); state.retryTimer = setTimeout(connect, 3000); };
    state.socket.onerror = markDisconnected;
  } catch (_) {
    markDisconnected();
    state.retryTimer = setTimeout(connect, 3000);
  }
}

async function hydrate() {
  try {
    const response = await fetch(`${state.endpoint}/api/v1/printers`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const printers = await response.json();
    render(Array.isArray(printers) ? printers[0] : printers.items?.[0]);
  } catch (_) {
    render(mockPrinter);
  }
}

function markDisconnected() {
  const conn = qs('connectionState');
  conn.classList.remove('online');
  conn.classList.add('offline');
  conn.querySelector('span:last-child').textContent = 'Gateway nicht erreichbar';
}

qs('pauseButton').addEventListener('click', () => command('pause'));
qs('resumeButton').addEventListener('click', () => command('resume'));
qs('stopButton').addEventListener('click', () => {
  if (confirm('Druck wirklich abbrechen?')) command('stop');
});

qs('cameraToggle').addEventListener('click', () => {
  state.cameraOn = !state.cameraOn;
  qs('cameraToggle').textContent = state.cameraOn ? 'Stoppen' : 'Starten';
  const view = qs('cameraViewport');
  if (!state.cameraOn) {
    view.innerHTML = '<span>Kamera aus</span>';
    return;
  }
  view.innerHTML = `<img alt="PRINTBENCH Kamera" src="${state.endpoint}/api/v1/printers/${encodeURIComponent(state.printer?.id || 'default')}/camera/snapshot" />`;
});

if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(console.warn);
render(mockPrinter);
connect();
