const address = document.body.dataset.address;
const badge = document.querySelector('.badge');
const latencyEl = document.getElementById('latency');
const packetLossEl = document.getElementById('packet-loss');
const sysNameEl = document.getElementById('sysname');
const lastCheckedEl = document.getElementById('last-checked');
const notesEl = document.getElementById('notes');
const stateEl = document.getElementById('state');
const deleteButton = document.getElementById('delete-host');

async function refreshHost() {
  const response = await fetch(`/api/hosts/${address}`);
  if (!response.ok) {
    stateEl.textContent = 'deleted';
    latencyEl.textContent = '—';
    packetLossEl.textContent = '—';
    sysNameEl.textContent = '—';
    lastCheckedEl.textContent = '—';
    notesEl.textContent = 'Host no longer tracked';
    badge.className = 'badge badge--pending';
    deleteButton.disabled = true;
    return;
  }
  const host = await response.json();
  badge.className = `badge badge--${host.state}`;
  latencyEl.textContent = host.latency_ms ? `${host.latency_ms.toFixed(1)} ms` : '—';
  packetLossEl.textContent = host.packet_loss_pct ? `${host.packet_loss_pct.toFixed(1)}%` : '—';
  sysNameEl.textContent = host.snmp_sysname || '—';
  lastCheckedEl.textContent = host.last_checked
    ? new Date(host.last_checked).toLocaleString()
    : '—';
  notesEl.textContent = host.notes && host.notes.length ? host.notes.join('; ') : '—';
  stateEl.textContent = host.state;
}

if (deleteButton) {
  deleteButton.addEventListener('click', async () => {
    deleteButton.disabled = true;
    const response = await fetch(`/api/hosts/${address}`, { method: 'DELETE' });
    if (response.ok) {
      window.location.href = '/';
      return;
    }
    deleteButton.disabled = false;
  });
}

refreshHost();
setInterval(refreshHost, 8000);
