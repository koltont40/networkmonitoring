# SNMP Network Monitoring Dashboard

A lightweight FastAPI-powered SNMP and ICMP monitor with a modern web dashboard. The service polls hosts for latency, packet loss, and basic SNMP metadata, and can push alerts to email and Slack when thresholds are exceeded.

## Features
- Periodic ICMP ping checks with latency and packet-loss tracking
- Optional SNMP `sysName` lookup per host
- Email and Slack notifications for failed or degraded hosts
- Live dashboard with manual rescan button
- Configurable polling interval and alert thresholds via environment variables

## Getting started
1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure hosts**
   Edit `config/hosts.yaml` and add your network devices. If the file is empty, demo hosts are used.

3. **(Optional) Configure alerts**
   Set environment variables to enable SMTP or Slack alerts:
   ```bash
   export MONITOR_SMTP_HOST=smtp.example.com
   export MONITOR_SMTP_PORT=587
   export MONITOR_SMTP_USERNAME=apikey
   export MONITOR_SMTP_PASSWORD=secret
   export MONITOR_SMTP_SENDER=monitor@example.com
   export MONITOR_SMTP_RECIPIENTS='["ops@example.com"]'
   export MONITOR_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
   ```

4. **Install & run in one step**
   ```bash
   ./install_and_run.sh
   ```
   The script provisions `.venv`, installs dependencies, loads `.env` if present, and starts uvicorn on port 8000. Visit [http://localhost:8000](http://localhost:8000) to view the dashboard.

## How monitoring works
- The polling loop runs every `MONITOR_MONITOR_INTERVAL_SECONDS` (default 30s).
- Alerts trigger when a host is unreachable or when latency/packet-loss exceeds configured thresholds. Repeat alerts are throttled to every 5 minutes per host.
- SNMP reads use the `SNMPv2-MIB::sysName.0` OID with the configured community string.

## Project layout
- `app/main.py` – FastAPI entrypoint, routes, and startup lifecycle
- `app/monitor.py` – Monitoring loop, ping + SNMP checks, and alert routing
- `app/notifications.py` – Email and Slack delivery helpers
- `app/templates/index.html` – Dashboard template
- `app/static/*` – Front-end styles and client polling logic
- `config/hosts.yaml` – Example host configuration
