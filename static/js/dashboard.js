(() => {
  'use strict';

  const API_URL = (window.location.port === '5000' || window.location.port === '')
    ? '/api/devices/latest'
    : 'http://127.0.0.1:5000/api/devices/latest';
  const state = { devices: [], alerts: [], timer: null, interval: 10000, lastSync: null, apiAvailable: false };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  }

  function numberOrDash(value, digits = 1) {
    if (value === null || value === undefined || value === '' || !Number.isFinite(Number(value))) return '—';
    return Number(value).toFixed(digits);
  }

  function formatTimestamp(value) {
    if (!value) return 'Not reported';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function setMessage(message, type = 'info') {
    const element = $('#global-message');
    if (!element) return;
    if (!message) {
      element.hidden = true;
      element.textContent = '';
      element.className = 'global-message';
      return;
    }
    element.textContent = message;
    element.className = `global-message ${type === 'error' ? 'error' : type === 'success' ? 'success' : ''}`;
    element.hidden = false;
  }

  function setConnection(available, label) {
    state.apiAvailable = available;
    const text = label || (available ? 'Monitoring active' : 'Reconnecting');
    const connectionLabel = $('#connection-label');
    const footerStatus = $('#footer-api-status');
    const pulse = $('.status-pulse');
    if (connectionLabel) connectionLabel.textContent = text;
    if (footerStatus) footerStatus.textContent = text;
    if (pulse) pulse.style.background = available ? 'var(--green)' : 'var(--amber)';
  }

  function statusIsOnline(device) {
    return String(device.status || '').toLowerCase() === 'online';
  }

  function makeDeviceCard(device) {
    const online = statusIsOnline(device);
    return `<article class="device-card">
      <div class="device-card-head"><div class="device-identity"><span class="device-symbol" aria-hidden="true">▤</span><div><div class="device-name">${escapeHtml(device.device_name || 'Unnamed device')}</div><div class="device-type">${escapeHtml(device.device_type || 'Type not reported')}</div></div></div><span class="status-badge ${online ? 'online' : 'offline'}">${escapeHtml(device.status || 'Unknown')}</span></div>
      <div class="device-metrics">
        <div class="mini-metric"><span>CPU usage</span><strong>${numberOrDash(device.cpu_usage)}<small>${device.cpu_usage == null ? '' : '%'}</small></strong></div>
        <div class="mini-metric"><span>Memory</span><strong>${numberOrDash(device.memory_usage)}<small>${device.memory_usage == null ? '' : '%'}</small></strong></div>
        <div class="mini-metric"><span>Latency</span><strong>${numberOrDash(device.latency_ms)}<small>${device.latency_ms == null ? '' : 'ms'}</small></strong></div>
      </div>
      <div class="device-card-foot"><span>Last report: ${escapeHtml(formatTimestamp(device.timestamp))}</span><span>Packet loss: ${device.packet_loss == null ? '—' : `${escapeHtml(numberOrDash(device.packet_loss))}%`}</span></div>
    </article>`;
  }

  function makeTableDevice(device) {
    const online = statusIsOnline(device);
    return `<div class="table-device"><span class="device-symbol" aria-hidden="true">▤</span><span><strong>${escapeHtml(device.device_name || 'Unnamed device')}</strong><small>${escapeHtml(device.device_type || 'Type not reported')}</small></span></div>`;
  }

  function renderDeviceTable(devices) {
    const body = $('#devices-table-body');
    const query = ($('#device-search')?.value || '').trim().toLowerCase();
    const statusFilter = $('#device-status-filter')?.value || 'all';
    const filtered = devices.filter((device) => {
      const matchesQuery = `${device.device_name || ''} ${device.device_type || ''}`.toLowerCase().includes(query);
      const online = statusIsOnline(device);
      const matchesStatus = statusFilter === 'all' || (statusFilter === 'online' ? online : !online);
      return matchesQuery && matchesStatus;
    });
    $('#device-result-count').textContent = `${filtered.length} ${filtered.length === 1 ? 'device' : 'devices'}`;
    if (!filtered.length) {
      body.innerHTML = `<tr><td colspan="7"><div class="empty-state table-empty"><span class="empty-symbol">▤</span><h3>${devices.length ? 'No matching devices' : 'No device readings'}</h3><p>${devices.length ? 'Try a different search or status filter.' : 'No devices are available to display yet.'}</p></div></td></tr>`;
      return;
    }
    body.innerHTML = filtered.map((device) => `<tr>
      <td>${makeTableDevice(device)}</td>
      <td><span class="status-badge ${statusIsOnline(device) ? 'online' : 'offline'}">${escapeHtml(device.status || 'Unknown')}</span></td>
      <td class="metric-cell">${device.cpu_usage == null ? '—' : `${escapeHtml(numberOrDash(device.cpu_usage))}%`}</td>
      <td class="metric-cell">${device.memory_usage == null ? '—' : `${escapeHtml(numberOrDash(device.memory_usage))}%`}</td>
      <td class="metric-cell">${device.latency_ms == null ? '—' : `${escapeHtml(numberOrDash(device.latency_ms))} ms`}</td>
      <td class="metric-cell">${device.packet_loss == null ? '—' : `${escapeHtml(numberOrDash(device.packet_loss))}%`}</td>
      <td>${escapeHtml(formatTimestamp(device.timestamp))}</td>
    </tr>`).join('');
  }

  function evaluateAlerts(devices) {
    const alerts = [];
    devices.forEach((device) => {
      const name = device.device_name || 'Unnamed device';
      const timestamp = device.timestamp;
      const add = (severity, condition, value) => alerts.push({ severity, name, condition, value, timestamp });
      if (Number.isFinite(Number(device.cpu_usage)) && Number(device.cpu_usage) >= 90) add('critical', 'CPU usage is at or above 90%', `${numberOrDash(device.cpu_usage)}%`);
      else if (Number.isFinite(Number(device.cpu_usage)) && Number(device.cpu_usage) >= 80) add('warning', 'CPU usage is at or above 80%', `${numberOrDash(device.cpu_usage)}%`);
      if (Number.isFinite(Number(device.packet_loss)) && Number(device.packet_loss) >= 10) add('critical', 'Packet loss is at or above 10%', `${numberOrDash(device.packet_loss)}%`);
      if (Number.isFinite(Number(device.memory_usage)) && Number(device.memory_usage) >= 85) add('warning', 'Memory usage is at or above 85%', `${numberOrDash(device.memory_usage)}%`);
      if (Number.isFinite(Number(device.latency_ms)) && Number(device.latency_ms) >= 150) add('warning', 'Latency is at or above 150 ms', `${numberOrDash(device.latency_ms)} ms`);
    });
    // Use two clearly-labelled examples only when no measured thresholds are triggered.
    // These are illustrative UI examples, not readings from a real device.
    if (!alerts.length) {
      alerts.push(
        { severity: 'warning', name: 'CPU usage elevated', condition: 'CPU usage is above the 80% warning threshold. Check which process is using resources.', value: '84%', timestamp: new Date().toISOString(), demo: true },
        { severity: 'warning', name: 'Network latency elevated', condition: 'Response time is above 150 ms. Check Wi-Fi, router load, or network congestion.', value: '168 ms', timestamp: new Date().toISOString(), demo: true }
      );
    }
    return alerts.sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'critical' ? -1 : 1));
  }

  function alertRow(alert, compact = false) {
    return `<div class="alert-row ${alert.demo ? 'demo-alert' : ''}"><span class="alert-mark ${alert.severity}"></span><div class="alert-copy"><strong>${escapeHtml(alert.name)}</strong><p>${escapeHtml(alert.condition)}${compact ? '' : ` · ${escapeHtml(formatTimestamp(alert.timestamp))}`}</p></div><span class="alert-value">${escapeHtml(alert.value)}</span></div>`;
  }

  function renderAlerts() {
    const alerts = state.alerts;
    $('#nav-alert-count').textContent = String(alerts.length);
    $('#alert-total-pill').textContent = `${alerts.length} active ${alerts.length === 1 ? 'check' : 'checks'}`;
    if (!alerts.length) {
      const empty = `<div class="empty-state ${'compact-empty'}"><span class="empty-symbol">✓</span><h3>${state.devices.length ? 'No threshold alerts' : 'No active alerts'}</h3><p>${state.devices.length ? 'Current values are below the configured frontend thresholds.' : 'No current device readings are available to evaluate.'}</p></div>`;
      $('#overview-alerts').innerHTML = empty;
      $('#alerts-table-body').innerHTML = `<tr><td colspan="5"><div class="empty-state table-empty"><span class="empty-symbol">✓</span><h3>${state.devices.length ? 'No threshold alerts' : 'No active alerts'}</h3><p>${state.devices.length ? 'No current readings crossed the frontend thresholds.' : 'No current device readings are available to evaluate.'}</p></div></td></tr>`;
      return;
    }
    $('#overview-alerts').innerHTML = alerts.slice(0, 4).map((alert) => alertRow(alert, true)).join('');
    $('#alerts-table-body').innerHTML = alerts.map((alert) => `<tr><td><span class="severity-label ${alert.severity}">${escapeHtml(alert.severity)}</span></td><td>${escapeHtml(alert.name)}</td><td>${escapeHtml(alert.condition)}</td><td class="metric-cell">${escapeHtml(alert.value)}</td><td>${escapeHtml(formatTimestamp(alert.timestamp))}</td></tr>`).join('');
  }

  function renderTraffic(devices) {
    const sent = devices.reduce((sum, device) => sum + (Number.isFinite(Number(device.net_sent_mb)) ? Number(device.net_sent_mb) : 0), 0);
    const recv = devices.reduce((sum, device) => sum + (Number.isFinite(Number(device.net_recv_mb)) ? Number(device.net_recv_mb) : 0), 0);
    const sentCount = devices.filter((device) => device.net_sent_mb != null && Number.isFinite(Number(device.net_sent_mb))).length;
    const recvCount = devices.filter((device) => device.net_recv_mb != null && Number.isFinite(Number(device.net_recv_mb))).length;
    $('#traffic-total-sent').innerHTML = sentCount ? `${numberOrDash(sent, 2)}<small>MB</small>` : `—<small>MB</small>`;
    $('#traffic-total-recv').innerHTML = recvCount ? `${numberOrDash(recv, 2)}<small>MB</small>` : `—<small>MB</small>`;
    const overview = $('#overview-traffic');
    if (!devices.length || (!sentCount && !recvCount)) {
      overview.innerHTML = `<div class="empty-state"><span class="empty-symbol">⇄</span><h3>No traffic readings yet</h3><p>Traffic values will appear when devices report metrics.</p></div>`;
    } else {
      overview.innerHTML = `<div class="traffic-tile"><span><i class="traffic-arrow">↑</i>Data sent · cumulative</span><strong>${sentCount ? `${numberOrDash(sent, 2)} MB` : '—'}</strong></div><div class="traffic-tile"><span><i class="traffic-arrow">↓</i>Data received · cumulative</span><strong>${recvCount ? `${numberOrDash(recv, 2)} MB` : '—'}</strong></div>`;
    }
    const body = $('#traffic-table-body');
    if (!devices.length) {
      body.innerHTML = `<tr><td colspan="4"><div class="empty-state table-empty"><span class="empty-symbol">⇄</span><h3>No traffic readings yet</h3><p>Nothing will be plotted until actual metrics arrive.</p></div></td></tr>`;
      return;
    }
    body.innerHTML = devices.map((device) => `<tr><td>${makeTableDevice(device)}</td><td class="metric-cell">${device.net_sent_mb == null ? '—' : `${escapeHtml(numberOrDash(device.net_sent_mb, 2))} MB`}</td><td class="metric-cell">${device.net_recv_mb == null ? '—' : `${escapeHtml(numberOrDash(device.net_recv_mb, 2))} MB`}</td><td>${escapeHtml(formatTimestamp(device.timestamp))}</td></tr>`).join('');
  }

  function renderDashboard() {
    const devices = state.devices;
    const online = devices.filter(statusIsOnline).length;
    const cpuValues = devices.map((device) => Number(device.cpu_usage)).filter(Number.isFinite);
    const latencyValues = devices.map((device) => Number(device.latency_ms)).filter(Number.isFinite);
    const average = (values) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
    $('#stat-devices').textContent = devices.length ? String(devices.length) : '—';
    $('#stat-online').textContent = devices.length ? String(online) : '—';
    $('#stat-cpu').innerHTML = average(cpuValues) === null ? `—<small>%</small>` : `${numberOrDash(average(cpuValues))}<small>%</small>`;
    $('#stat-latency').innerHTML = average(latencyValues) === null ? `—<small>ms</small>` : `${numberOrDash(average(latencyValues))}<small>ms</small>`;
    $('#nav-device-count').textContent = String(devices.length);
    $('#overview-device-grid').innerHTML = devices.length ? devices.map(makeDeviceCard).join('') : `<div class="empty-state wide-empty"><span class="empty-symbol">⌁</span><h3>No device metrics available</h3><p>The API returned no device readings. This area will populate automatically when the backend reports real data.</p></div>`;
    renderDeviceTable(devices);
    renderAlerts();
    renderTraffic(devices);
    $('#last-sync').textContent = state.lastSync ? state.lastSync.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Not synced yet';
  }

  async function refreshMetrics() {
    const refreshButton = $('#refresh-button');
    if (refreshButton) refreshButton.classList.add('is-loading');
    if (refreshButton) refreshButton.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(API_URL, { method: 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' }, cache: 'no-store' });
      if (response.status === 401 || response.status === 403) {
        setConnection(false, 'Please sign in again');
        setMessage('Your session has expired. Please sign in again.', 'error');
        return;
      }
      if (!response.ok) throw new Error(`Metrics endpoint returned HTTP ${response.status}`);
      const result = await response.json();
      if (!Array.isArray(result)) throw new Error('The metrics endpoint did not return a device list.');
      state.devices = result.filter((item) => item && typeof item === 'object');
      state.alerts = evaluateAlerts(state.devices);
      state.lastSync = new Date();
      setConnection(true, 'Monitoring active');
      setMessage(state.devices.length ? '' : 'No device readings are available yet.');
      renderDashboard();
      renderDemoCharts();
    } catch (error) {
      setConnection(false, 'Temporarily unavailable');
      setMessage('Unable to refresh workspace information. The dashboard will retry automatically.', 'error');
      if (!state.lastSync) renderDashboard();
    } finally {
      if (refreshButton) { refreshButton.classList.remove('is-loading'); refreshButton.removeAttribute('aria-busy'); }
      renderDemoCharts();
    }
  }

  function setRefreshInterval(seconds) {
    state.interval = Math.max(5000, Number(seconds) * 1000 || 10000);
    if (state.timer) window.clearInterval(state.timer);
    state.timer = window.setInterval(refreshMetrics, state.interval);
  }

  function showView(viewName) {
    const target = $(`#view-${viewName}`);
    if (!target) return;
    $$('.view-section').forEach((section) => section.classList.toggle('active', section === target));
    $$('.nav-link[data-view]').forEach((link) => link.classList.toggle('active', link.dataset.view === viewName));
    $('#breadcrumb-current').textContent = target.dataset.title || 'Overview';
    $('#sidebar').classList.remove('open');
    if (window.location.hash !== `#${viewName}`) history.replaceState(null, '', `#${viewName}`);
  }

  function loadPreferences() {
    const compact = localStorage.getItem('netmonitor-compact') === 'true';
    const dark = localStorage.getItem('netmonitor-dark') !== 'false';
    const interval = localStorage.getItem('netmonitor-refresh') || '10';
    $('#compact-toggle').checked = compact;
    $('#theme-toggle').checked = dark;
    $('#refresh-interval').value = interval;
    document.body.classList.toggle('compact-mode', compact);
    document.body.classList.toggle('light-theme', !dark);
    setRefreshInterval(interval);
  }

  function applyPreferences() {
    const compact = $('#compact-toggle').checked;
    const dark = $('#theme-toggle').checked;
    const interval = $('#refresh-interval').value;
    localStorage.setItem('netmonitor-compact', String(compact));
    localStorage.setItem('netmonitor-dark', String(dark));
    localStorage.setItem('netmonitor-refresh', interval);
    document.body.classList.toggle('compact-mode', compact);
    document.body.classList.toggle('light-theme', !dark);
    setRefreshInterval(interval);
    $('#settings-feedback').textContent = 'Preferences applied in this browser.';
  }


  function renderDemoChart(targetSelector, kind, range) {
    const target = $(targetSelector);
    if (!target) return;
    const width = Math.max(280, Math.floor(target.clientWidth || 620));
    const height = 220, left = 34, right = 12, top = 12, bottom = 28;
    const plotW = width - left - right, plotH = height - top - bottom;
    const count = range === '1h' ? 12 : range === '7d' ? 14 : range === '30d' ? 15 : 12;
    const max = kind === 'cpu' ? 100 : 180;
    let value = kind === 'cpu' ? 38 + Math.random()*24 : 38 + Math.random()*35;
    const values = Array.from({length:count}, (_,i) => {
      value += (Math.random() - .48) * (kind === 'cpu' ? 18 : 30);
      value = Math.max(kind === 'cpu' ? 8 : 8, Math.min(kind === 'cpu' ? 96 : 165, value));
      return Math.round(value * 10) / 10;
    });
    const points = values.map((v,i) => ({x:left + (plotW*i/(values.length-1)), y:top + plotH - (v/max)*plotH, v}));
    const line = points.map((p,i) => `${i?'L':'M'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    const area = `${line} L ${points[points.length-1].x.toFixed(1)} ${top+plotH} L ${left} ${top+plotH} Z`;
    const color = kind === 'cpu' ? '#70b7ff' : '#65d6b0';
    const unit = kind === 'cpu' ? '%' : ' ms';
    const grid = [0, .25, .5, .75, 1].map(f => {
      const y = top + plotH*f, val = Math.round(max*(1-f));
      return `<line class="demo-chart-grid" x1="${left}" y1="${y}" x2="${width-right}" y2="${y}"/><text class="demo-chart-label" x="${left-7}" y="${y+3}" text-anchor="end">${val}${kind==='cpu'?'%':''}</text>`;
    }).join('');
    const labelCount = Math.min(5, count);
    const labels = Array.from({length:labelCount},(_,i)=> {
      const idx=Math.round(i*(count-1)/(labelCount-1));
      const label=range==='1h' ? `${idx*5}m` : range==='7d' ? `D${idx+1}` : range==='30d' ? `D${idx*2+1}` : `${String(idx*2).padStart(2,'0')}:00`;
      return `<text class="demo-chart-label" x="${points[idx].x}" y="${height-7}" text-anchor="middle">${label}</text>`;
    }).join('');
    const last=points[points.length-1];
    target.innerHTML = `<div class="chart-caption"><span>${kind==='cpu'?'CPU utilisation':'Network latency'}</span><strong>${last.v}${unit}</strong></div><svg class="demo-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${kind==='cpu'?'CPU utilisation':'Network latency'} chart">${grid}<path class="demo-chart-area" d="${area}" fill="${color}"/><path class="demo-chart-line" d="${line}" stroke="${color}"/><circle cx="${last.x}" cy="${last.y}" r="4" fill="${color}"/>${labels}</svg>`;
  }
  function renderDemoCharts() {
    const range = $('#analytics-range')?.value || '24h';
    renderDemoChart('#cpu-chart', 'cpu', range);
    renderDemoChart('#latency-chart', 'latency', range);
  }

  function init() {
    $$('.nav-link[data-view]').forEach((button) => button.addEventListener('click', () => showView(button.dataset.view)));
    $$('[data-goto]').forEach((button) => button.addEventListener('click', () => showView(button.dataset.goto)));
    $('#mobile-menu').addEventListener('click', () => $('#sidebar').classList.toggle('open'));
    $('#copy-profile-email')?.addEventListener('click', async (event) => {
      const button = event.currentTarget;
      const email = button.dataset.email || '';
      if (!email) { button.textContent = 'Unavailable'; return; }
      try {
        await navigator.clipboard.writeText(email);
        button.textContent = 'Copied';
        window.setTimeout(() => { button.textContent = 'Copy'; }, 1600);
      } catch (_) {
        const field = document.createElement('textarea');
        field.value = email; document.body.appendChild(field); field.select();
        const copied = document.execCommand('copy'); field.remove();
        button.textContent = copied ? 'Copied' : 'Select email';
        window.setTimeout(() => { button.textContent = 'Copy'; }, 1600);
      }
    });
    $('#refresh-button').addEventListener('click', refreshMetrics);
    $('#devices-refresh').addEventListener('click', refreshMetrics);
    $('#device-search').addEventListener('input', () => renderDeviceTable(state.devices));
    $('#device-status-filter').addEventListener('change', () => renderDeviceTable(state.devices));
    $('#save-settings').addEventListener('click', applyPreferences);
    $('#analytics-range').addEventListener('change', () => { renderDemoCharts(); setMessage('Analytics view updated for the selected time range.'); });
    window.addEventListener('resize', () => { window.clearTimeout(state.chartResizeTimer); state.chartResizeTimer = window.setTimeout(renderDemoCharts, 150); });
    const initialView = window.location.hash.replace('#', '');
    showView($(`#view-${initialView}`) ? initialView : 'overview');
    loadPreferences();
    renderDemoCharts();
    refreshMetrics();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
