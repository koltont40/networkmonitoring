const address = document.body.dataset.address;
const badge = document.querySelector('.badge');
const latencyEl = document.getElementById('latency');
const latencyMinEl = document.getElementById('latency-min');
const latencyMaxEl = document.getElementById('latency-max');
const packetLossEl = document.getElementById('packet-loss');
const successRateEl = document.getElementById('success-rate');
const packetsEl = document.getElementById('packets');
const sysNameEl = document.getElementById('sysname');
const lastCheckedEl = document.getElementById('last-checked');
const lastAlertEl = document.getElementById('last-alert');
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
  latencyEl.textContent = host.latency_ms != null ? `${host.latency_ms.toFixed(1)} ms` : '—';
  latencyMinEl.textContent = host.latency_min_ms != null ? `${host.latency_min_ms.toFixed(1)} ms` : '—';
  latencyMaxEl.textContent = host.latency_max_ms != null ? `${host.latency_max_ms.toFixed(1)} ms` : '—';
  packetLossEl.textContent = host.packet_loss_pct != null ? `${host.packet_loss_pct.toFixed(1)}%` : '—';
  successRateEl.textContent = host.packet_success_pct != null ? `${host.packet_success_pct.toFixed(1)}%` : '—';
  packetsEl.textContent = host.packets_received != null && host.packets_sent != null
    ? `${host.packets_received}/${host.packets_sent}`
    : '—';
  sysNameEl.textContent = host.snmp_sysname || '—';
  lastCheckedEl.textContent = host.last_checked
    ? new Date(host.last_checked).toLocaleString()
    : '—';
  lastAlertEl.textContent = host.last_alert
    ? new Date(host.last_alert).toLocaleString()
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
const pollIntervalMs = Math.max(4000, Number(document.body.dataset.pollInterval || '8') * 1000);
setInterval(refreshHost, pollIntervalMs);
