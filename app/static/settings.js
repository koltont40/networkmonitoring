function serializeForm(form) {
  const data = new FormData(form);
  const payload = {};
  for (const [key, value] of data.entries()) {
    if (value === '') {
      payload[key] = null;
      continue;
    }
    if (['monitor_interval_seconds', 'latency_threshold_ms', 'packet_loss_threshold_pct', 'smtp_port', 'snmp_port'].includes(key)) {
      payload[key] = Number(value);
    } else {
      payload[key] = value;
    }
  }
  return payload;
}

async function postSettings(formId, statusId) {
  const form = document.getElementById(formId);
  const status = document.getElementById(statusId);
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    status.textContent = 'Saving...';
    status.classList.remove('text--error');
    const payload = serializeForm(form);

    try {
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        status.textContent = 'Failed to save settings';
        status.classList.add('text--error');
        return;
      }

      status.textContent = 'Saved';
      setTimeout(() => (status.textContent = ''), 2000);
    } catch (error) {
      status.textContent = error.message || 'Unexpected error';
      status.classList.add('text--error');
    }
  });
}

postSettings('settings-form', 'settings-status');
postSettings('alerts-form', 'alerts-status');

const addForm = document.getElementById('add-hosts-form');
const rangeInput = document.getElementById('range');
const communityInput = document.getElementById('community');
const snmpPortInput = document.getElementById('snmp-port');
const statusEl = document.getElementById('add-status');

if (addForm) {
  addForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    statusEl.textContent = 'Adding hosts...';
    statusEl.classList.remove('text--error');
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
      statusEl.textContent = `Added ${result.added} host(s)` + (result.skipped ? `, skipped ${result.skipped}` : '');
    } catch (error) {
      statusEl.textContent = error.message || 'Unexpected error';
      statusEl.classList.add('text--error');
    }
  });
}
