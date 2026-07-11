(() => {
  const devStatus = document.getElementById('devStatus');
  const recStatus = document.getElementById('recStatus');
  const btnStart = document.getElementById('btnStart');
  const btnStop = document.getElementById('btnStop');

  async function refreshStatus() {
    const r = await fetch('/api/status');
    const s = await r.json();
    devStatus.textContent =
        s.device_connected ? 'Connected ✅' : 'Disconnected ❌';
    recStatus.textContent = s.recording ? 'Recording 🔴' : 'Stopped ⚪';
    btnStart.disabled = !s.device_connected || s.recording;
    btnStop.disabled = !s.device_connected || !s.recording;
  }

  async function post(path) {
    const r = await fetch(path, {method: 'POST'});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) alert(j.error || 'Error');
    await refreshStatus();
  }

  btnStart?.addEventListener('click', () => post('/api/start'));
  btnStop?.addEventListener('click', () => post('/api/stop'));

  refreshStatus();
  setInterval(refreshStatus, 1000);
})();
