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

const addForm = document.getElementById('add-hosts-form');
const rangeInput = document.getElementById('range');
const communityInput = document.getElementById('community');
const snmpPortInput = document.getElementById('snmp-port');
const statusEl = document.getElementById('add-status');

addForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  statusEl.textContent = 'Adding hosts...';
  const payload = {
    range: rangeInput.value.trim(),
    community: communityInput.value.trim() || null,
    snmp_port: snmpPortInput.value ? Number(snmpPortInput.value) : null,
  };

  try {
    const response = await fetch('/api/hosts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      statusEl.textContent = error.detail || 'Failed to add hosts';
      statusEl.classList.add('text--error');
      return;
    }

    const result = await response.json();
    statusEl.classList.remove('text--error');
    statusEl.textContent = `Added ${result.added} host(s)` + (result.skipped ? `, skipped ${result.skipped}` : '');
    if (result.added) {
      await fetchHosts();
    }
  } catch (error) {
    statusEl.textContent = error.message || 'Unexpected error';
    statusEl.classList.add('text--error');
  }
});
