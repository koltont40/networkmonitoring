const address = document.body.dataset.address;
const badge = document.querySelector('.badge');
const latencyEl = document.getElementById('latency');
const latencyMinEl = document.getElementById('latency-min');
const latencyMaxEl = document.getElementById('latency-max');
const packetLossEl = document.getElementById('packet-loss');
const successRateEl = document.getElementById('success-rate');
const packetsEl = document.getElementById('packets');
const sysNameEl = document.getElementById('sysname');
const cpuEl = document.getElementById('cpu');
const memoryEl = document.getElementById('memory');
const interfaceTempEl = document.getElementById('interface-temp');
const systemTempEl = document.getElementById('system-temp');
const psuStatusEl = document.getElementById('psu-status');
const throughputEl = document.getElementById('throughput');
const lastCheckedEl = document.getElementById('last-checked');
const lastAlertEl = document.getElementById('last-alert');
const notesEl = document.getElementById('notes');
const stateEl = document.getElementById('state');
const deleteButton = document.getElementById('delete-host');
const healthChartCtx = document.getElementById('health-chart')?.getContext('2d');
const systemChartCtx = document.getElementById('system-chart')?.getContext('2d');
const interfaceChartCtx = document.getElementById('interface-chart')?.getContext('2d');
const throughputChartCtx = document.getElementById('throughput-chart')?.getContext('2d');

let healthChart;
let systemChart;
let interfaceChart;
let throughputChart;
let latestSampleTimestamp;

function formatTimestamp(iso) {
  return new Date(iso).toLocaleTimeString();
}

function buildOrUpdateCharts(history) {
  if (!healthChartCtx || !interfaceChartCtx || !throughputChartCtx || !systemChartCtx) return;

  const labels = history.map((entry) => formatTimestamp(entry.timestamp));
  const latencyData = history.map((entry) => entry.latency_ms ?? null);
  const packetLossData = history.map((entry) => entry.packet_loss_pct ?? null);
  const successData = history.map((entry) => entry.packet_success_pct ?? null);
  const packetsReceived = history.map((entry) => entry.packets_received ?? null);
  const cpuUsage = history.map((entry) => entry.cpu_usage_pct ?? null);
  const memoryUsage = history.map((entry) => entry.memory_used_pct ?? null);
  const interfaceTemp = history.map((entry) => entry.interface_temp_c ?? null);
  const systemTemp = history.map((entry) => entry.system_temp_c ?? null);
  const ingress = history.map((entry) =>
    entry.interface_in_bps != null ? entry.interface_in_bps / 1_000_000 : null
  );
  const egress = history.map((entry) =>
    entry.interface_out_bps != null ? entry.interface_out_bps / 1_000_000 : null
  );

  if (!healthChart) {
    healthChart = new Chart(healthChartCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Latency (ms)',
            data: latencyData,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.15)',
            tension: 0.25,
            spanGaps: true,
            yAxisID: 'y',
          },
          {
            label: 'Packet loss (%)',
            data: packetLossData,
            borderColor: '#e34c26',
            backgroundColor: 'rgba(227, 76, 38, 0.18)',
            borderDash: [6, 6],
            tension: 0.25,
            spanGaps: true,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            title: { display: true, text: 'Latency (ms)' },
            beginAtZero: true,
            ticks: { color: '#e6edf3' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
          y1: {
            position: 'right',
            title: { display: true, text: 'Packet loss (%)' },
            beginAtZero: true,
            ticks: { color: '#e6edf3' },
            grid: { drawOnChartArea: false },
            suggestedMax: 100,
          },
          x: {
            ticks: { color: '#e6edf3' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
        },
        plugins: {
          legend: { labels: { color: '#e6edf3' } },
        },
      },
    });
  } else {
    healthChart.data.labels = labels;
    healthChart.data.datasets[0].data = latencyData;
    healthChart.data.datasets[1].data = packetLossData;
    healthChart.update();
  }

  if (!interfaceChart) {
    interfaceChart = new Chart(interfaceChartCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Packet success (%)',
            data: successData,
            borderColor: '#2ea043',
            backgroundColor: 'rgba(46, 160, 67, 0.18)',
            tension: 0.25,
            spanGaps: true,
            yAxisID: 'y',
          },
          {
            label: 'Packets received',
            data: packetsReceived,
            borderColor: '#f0b429',
            backgroundColor: 'rgba(240, 180, 41, 0.18)',
            tension: 0.25,
            spanGaps: true,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            suggestedMax: 100,
            title: { display: true, text: 'Success (%)' },
            ticks: { color: '#e6edf3' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
          y1: {
            position: 'right',
            beginAtZero: true,
            title: { display: true, text: 'Packets' },
            ticks: { color: '#e6edf3' },
            grid: { drawOnChartArea: false },
          },
          x: {
            ticks: { color: '#e6edf3' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
        },
        plugins: {
          legend: { labels: { color: '#e6edf3' } },
        },
      },
    });
  } else {
    interfaceChart.data.labels = labels;
    interfaceChart.data.datasets[0].data = successData;
    interfaceChart.data.datasets[1].data = packetsReceived;
    interfaceChart.update();
  }

  if (!throughputChart) {
    throughputChart = new Chart(throughputChartCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Ingress (Mbps)',
            data: ingress,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.18)',
            tension: 0.25,
            spanGaps: true,
          },
          {
            label: 'Egress (Mbps)',
            data: egress,
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.18)',
            tension: 0.25,
            spanGaps: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Throughput (Mbps)' },
            ticks: { color: '#e6edf3' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
          x: {
            ticks: { color: '#e6edf3' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
        },
        plugins: {
          legend: { labels: { color: '#e6edf3' } },
        },
      },
    });
  } else {
    throughputChart.data.labels = labels;
    throughputChart.data.datasets[0].data = ingress;
    throughputChart.data.datasets[1].data = egress;
    throughputChart.update();
  }

  if (!systemChart) {
    systemChart = new Chart(systemChartCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'CPU usage (%)',
            data: cpuUsage,
            borderColor: '#8b5cf6',
            backgroundColor: 'rgba(139, 92, 246, 0.18)',
            tension: 0.25,
            spanGaps: true,
          },
          {
            label: 'Memory used (%)',
            data: memoryUsage,
            borderColor: '#ec4899',
            backgroundColor: 'rgba(236, 72, 153, 0.18)',
            tension: 0.25,
            spanGaps: true,
          },
          {
            label: 'Interface temp (°C)',
            data: interfaceTemp,
            borderColor: '#22d3ee',
            backgroundColor: 'rgba(34, 211, 238, 0.18)',
            tension: 0.25,
            spanGaps: true,
          },
          {
            label: 'System temp (°C)',
            data: systemTemp,
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.18)',
            tension: 0.25,
            spanGaps: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            suggestedMax: 100,
            title: { display: true, text: 'Utilization (%)' },
            ticks: { color: '#e6edf3' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
          x: {
            ticks: { color: '#e6edf3' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
        },
        plugins: {
          legend: { labels: { color: '#e6edf3' } },
        },
      },
    });
  } else {
    systemChart.data.labels = labels;
    systemChart.data.datasets[0].data = cpuUsage;
    systemChart.data.datasets[1].data = memoryUsage;
    systemChart.data.datasets[2].data = interfaceTemp;
    systemChart.data.datasets[3].data = systemTemp;
    systemChart.update();
  }
}

async function refreshHistory() {
  const response = await fetch(`/api/hosts/${address}/history`);
  if (!response.ok) return;
  const history = await response.json();
  if (!history.length) return;
  latestSampleTimestamp = history[history.length - 1].timestamp;
  buildOrUpdateCharts(history);
}

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
  cpuEl.textContent = host.cpu_usage_pct != null ? `${host.cpu_usage_pct.toFixed(1)}%` : '—';
  memoryEl.textContent =
    host.memory_used_pct != null ? `${host.memory_used_pct.toFixed(1)}%` : '—';
  interfaceTempEl.textContent =
    host.interface_temp_c != null ? `${host.interface_temp_c.toFixed(1)}°C` : '—';
  systemTempEl.textContent =
    host.system_temp_c != null ? `${host.system_temp_c.toFixed(1)}°C` : '—';
  throughputEl.textContent =
    host.interface_in_bps != null && host.interface_out_bps != null
      ? `${(host.interface_in_bps / 1_000_000).toFixed(2)} / ${(host.interface_out_bps / 1_000_000).toFixed(2)} Mbps`
      : '—';
  psuStatusEl.textContent = host.psu_status || '—';
  lastCheckedEl.textContent = host.last_checked
    ? new Date(host.last_checked).toLocaleString()
    : '—';
  lastAlertEl.textContent = host.last_alert
    ? new Date(host.last_alert).toLocaleString()
    : '—';
  notesEl.textContent = host.notes && host.notes.length ? host.notes.join('; ') : '—';
  stateEl.textContent = host.state;

  if (host.last_checked) {
    const lastCheckedTime = new Date(host.last_checked).getTime();
    const latestKnown = latestSampleTimestamp
      ? new Date(latestSampleTimestamp).getTime()
      : 0;
    if (!latestSampleTimestamp || lastCheckedTime > latestKnown) {
      refreshHistory();
    }
  }
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
refreshHistory();
const pollIntervalMs = Math.max(4000, Number(document.body.dataset.pollInterval || '8') * 1000);
setInterval(refreshHost, pollIntervalMs);
