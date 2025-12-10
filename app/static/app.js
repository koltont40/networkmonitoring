async function fetchHosts() {
  const response = await fetch('/api/hosts');
  if (!response.ok) return;
  const hosts = await response.json();
  const tableBody = document.getElementById('table-body');
  tableBody.innerHTML = '';
  hosts.forEach((host) => {
    const row = document.createElement('div');
    row.className = 'table__row';
    row.innerHTML = `
      <div class="table__cell">
        <span class="badge badge--${host.state}" aria-hidden="true"></span>
        <div>
          <div class="host">${host.name}</div>
          <div class="muted">${host.address}</div>
        </div>
      </div>
      <div class="table__cell">${host.latency_ms ? host.latency_ms.toFixed(1) : '—'}</div>
      <div class="table__cell">${host.packet_loss_pct ? host.packet_loss_pct.toFixed(1) : '—'}</div>
      <div class="table__cell">${host.snmp_sysname || '—'}</div>
      <div class="table__cell">${host.last_checked ? new Date(host.last_checked).toLocaleTimeString() : '—'}</div>
      <div class="table__cell">${host.notes && host.notes.length ? host.notes.join('; ') : '—'}</div>
    `;
    tableBody.appendChild(row);
  });
}

async function triggerRescan() {
  const button = document.getElementById('rescan');
  button.disabled = true;
  button.textContent = 'Rescanning...';
  try {
    await fetch('/api/rescan', { method: 'POST' });
    await fetchHosts();
  } finally {
    button.disabled = false;
    button.textContent = 'Rescan now';
  }
}

fetchHosts();
setInterval(fetchHosts, 8000);

document.getElementById('rescan').addEventListener('click', triggerRescan);
