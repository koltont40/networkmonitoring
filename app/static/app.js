async function fetchHosts() {
  const response = await fetch('/api/hosts?reachable_only=true');
  if (!response.ok) return;
  const hosts = await response.json();
  const tableBody = document.getElementById('table-body');
  tableBody.innerHTML = '';
  if (!hosts.length) {
    const empty = document.createElement('div');
    empty.className = 'table__row table__row--empty';
    empty.textContent = 'No active hosts detected.';
    tableBody.appendChild(empty);
    return;
  }
  hosts.forEach((host) => {
    const row = document.createElement('div');
    row.className = 'table__row';
    row.innerHTML = `
      <div class="table__cell">
        <span class="badge badge--${host.state}" aria-hidden="true"></span>
        <div>
          <div class="host">${host.name}</div>
          <div class="muted"><a href="/hosts/${host.address}">${host.address}</a></div>
        </div>
      </div>
      <div class="table__cell">${host.latency_ms != null ? host.latency_ms.toFixed(1) : '—'}</div>
      <div class="table__cell">${host.packet_loss_pct != null ? host.packet_loss_pct.toFixed(1) : '—'}</div>
      <div class="table__cell">${host.snmp_sysname || '—'}</div>
      <div class="table__cell">${host.last_checked ? new Date(host.last_checked).toLocaleTimeString() : '—'}</div>
      <div class="table__cell">${host.notes && host.notes.length ? host.notes.join('; ') : '—'}</div>
      <div class="table__cell table__cell--actions"><button class="ghost" data-address="${host.address}">Delete</button></div>
    `;
    tableBody.appendChild(row);
  });

  document.querySelectorAll('.table__cell--actions button').forEach((button) => {
    button.addEventListener('click', async (event) => {
      const address = event.currentTarget.getAttribute('data-address');
      event.currentTarget.disabled = true;
      try {
        const response = await fetch(`/api/hosts/${address}`, { method: 'DELETE' });
        if (!response.ok) {
          event.currentTarget.disabled = false;
          return;
        }
        await fetchHosts();
      } catch (error) {
        event.currentTarget.disabled = false;
      }
    });
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
const pollIntervalMs = Math.max(4000, Number(document.body.dataset.pollInterval || '8') * 1000);
setInterval(fetchHosts, pollIntervalMs);

document.getElementById('rescan').addEventListener('click', triggerRescan);

const addForm = document.getElementById('add-hosts-form');
const rangeInput = document.getElementById('range');
const communityInput = document.getElementById('community');
const snmpPortInput = document.getElementById('snmp-port');
const interfaceIndexInput = document.getElementById('interface-index');
const statusEl = document.getElementById('add-status');

addForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  statusEl.textContent = 'Adding hosts...';
  const payload = {
    range: rangeInput.value.trim(),
    community: communityInput.value.trim() || null,
    snmp_port: snmpPortInput.value ? Number(snmpPortInput.value) : null,
    interface_index: interfaceIndexInput.value ? Number(interfaceIndexInput.value) : null,
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
