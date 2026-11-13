/**
 * CabinetSense AI - Frontend Application & SCADA Controller
 * Handles SPA navigation, real-time Chart.js telemetry rendering,
 * live polling, simulation triggers, and alert acknowledgement.
 */

class CabinetSenseApp {
  constructor() {
    this.apiBase = "/api";
    this.pollIntervalMs = 1500;
    this.chartHistoryLimit = 30;
    this.selectedScenario = "normal";
    this.currentAlertFilter = "ALL";
    this.pollTimer = null;
    
    // Chart instances
    this.charts = {
      overviewTemp: null,
      overviewHum: null,
      liveTemp: null,
      liveHum: null
    };

    this.init();
  }

  init() {
    this.setupNavigation();
    this.setupSidebarToggle();
    this.setupClock();
    this.initCharts();
    this.startPolling();
    this.refreshIcons();
    
    // Initial fetch
    this.fetchSystemStatus();
    this.fetchReadings();
    this.fetchAlerts();
    this.fetchAnalytics();
    this.fetchAIStatus();
  }

  refreshIcons() {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  // -------------------------------------------------------------
  // NAVIGATION & UI
  // -------------------------------------------------------------

  setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const page = link.getAttribute('data-page');
        this.navigate(page);
      });
    });

    // Hash navigation support
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.replace('#', '') || 'overview';
      this.navigate(hash);
    });

    if (window.location.hash) {
      this.navigate(window.location.hash.replace('#', ''));
    }
  }

  navigate(pageId) {
    const pages = {
      'overview': { title: 'Operational Overview', desc: 'Real-time industrial electrical cabinet environmental diagnostics' },
      'monitoring': { title: 'Live SCADA Monitoring', desc: 'Continuous high-resolution temperature and humidity sensor streams' },
      'ai-center': { title: 'AI Intelligence Center', desc: 'Unsupervised Isolation Forest anomaly detection and thermodynamic modeling' },
      'anomalies': { title: 'Anomaly Detection Registry', desc: 'Audit log of unusual multivariate environmental signatures' },
      'alerts': { title: 'SCADA Alerts Center', desc: 'Alarm management console and threshold breach acknowledgment' },
      'analytics': { title: 'Historical Analytics', desc: 'Long-term telemetry distributions and laboratory export' },
      'simulation': { title: 'Simulation Laboratory', desc: 'Multi-scenario industrial environmental hazard injection engine' },
      'settings': { title: 'System Settings', desc: 'Hardware pinouts, reference thresholds, and connection diagnostics' }
    };

    const target = pages[pageId] ? pageId : 'overview';
    const info = pages[target];

    // Toggle view sections
    document.querySelectorAll('.page-view').forEach(view => view.classList.remove('active'));
    const activeView = document.getElementById(`view-${target}`);
    if (activeView) activeView.classList.add('active');

    // Toggle nav active state
    document.querySelectorAll('.nav-link').forEach(link => {
      link.classList.toggle('active', link.getAttribute('data-page') === target);
    });

    // Update topbar titles
    document.getElementById('current-page-title').textContent = info.title;
    document.getElementById('current-page-desc').textContent = info.desc;
    window.location.hash = target;

    // Refresh charts if entering chart views
    if (target === 'monitoring' || target === 'overview') {
      setTimeout(() => {
        Object.values(this.charts).forEach(c => c && c.resize());
      }, 100);
    }

    this.refreshIcons();
  }

  setupSidebarToggle() {
    const toggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        setTimeout(() => {
          Object.values(this.charts).forEach(c => c && c.resize());
        }, 300);
      });
    }
  }

  setupClock() {
    const updateTime = () => {
      const now = new Date();
      const utcString = now.toUTCString().split(' ')[4] + ' UTC';
      const clockEl = document.getElementById('live-clock');
      const sideEl = document.getElementById('sidebar-time');
      if (clockEl) clockEl.textContent = utcString;
      if (sideEl) sideEl.textContent = utcString;
    };
    updateTime();
    setInterval(updateTime, 1000);
  }

  // -------------------------------------------------------------
  // TOAST NOTIFICATIONS
  // -------------------------------------------------------------

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let iconName = 'info';
    if (type === 'critical' || type === 'error') iconName = 'alert-triangle';
    if (type === 'success') iconName = 'check-circle';
    if (type === 'warning') iconName = 'alert-circle';

    toast.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px;">
        <i data-lucide="${iconName}"></i>
        <div style="font-size: 13px;">${message}</div>
      </div>
      <button style="background: none; border: none; color: var(--text-muted); cursor: pointer;" onclick="this.parentElement.remove()">✕</button>
    `;

    container.appendChild(toast);
    this.refreshIcons();

    setTimeout(() => {
      if (toast.parentElement) toast.remove();
    }, 4500);
  }

  // -------------------------------------------------------------
  // CHART INITIALIZATION & MANAGEMENT
  // -------------------------------------------------------------

  getChartCommonOptions(yTitle, yMin, yMax, unit = '') {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#101B30',
          titleColor: '#F8FAFC',
          bodyColor: '#94A3B8',
          borderColor: 'rgba(37, 99, 235, 0.4)',
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y} ${unit}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.04)' },
          ticks: { color: '#64748B', font: { family: 'JetBrains Mono', size: 10 } }
        },
        y: {
          min: yMin,
          max: yMax,
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#94A3B8', font: { family: 'JetBrains Mono', size: 10 } },
          title: { display: true, text: yTitle, color: '#64748B', font: { size: 11 } }
        }
      }
    };
  }

  initCharts() {
    // 1. Overview Temp Chart
    const otCanvas = document.getElementById('overviewTempChart');
    if (otCanvas) {
      this.charts.overviewTemp = new Chart(otCanvas.getContext('2d'), {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: 'Temperature',
            data: [],
            borderColor: '#22D3EE',
            backgroundColor: 'rgba(34, 211, 238, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 5
          }]
        },
        options: this.getChartCommonOptions('Temperature (°C)', 15, 65, '°C')
      });
    }

    // 2. Overview Hum Chart
    const ohCanvas = document.getElementById('overviewHumChart');
    if (ohCanvas) {
      this.charts.overviewHum = new Chart(ohCanvas.getContext('2d'), {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: 'Humidity',
            data: [],
            borderColor: '#3B82F6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 5
          }]
        },
        options: this.getChartCommonOptions('Humidity (%)', 15, 95, '%')
      });
    }

    // 3. Live Temp Chart (With Threshold Safety Reference Line)
    const ltCanvas = document.getElementById('liveTempChart');
    if (ltCanvas) {
      this.charts.liveTemp = new Chart(ltCanvas.getContext('2d'), {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Cabinet Temperature',
              data: [],
              borderColor: '#22D3EE',
              backgroundColor: 'rgba(34, 211, 238, 0.08)',
              fill: true,
              tension: 0.3,
              borderWidth: 2.5,
              pointRadius: 3,
              pointBackgroundColor: (ctx) => {
                const index = ctx.dataIndex;
                const reading = ctx.dataset.rawReadings ? ctx.dataset.rawReadings[index] : null;
                return (reading && reading.is_anomaly) ? '#EF4444' : '#22D3EE';
              }
            },
            {
              label: 'Warning Limit (38°C)',
              data: [],
              borderColor: 'rgba(245, 158, 11, 0.5)',
              borderDash: [5, 5],
              borderWidth: 1.5,
              pointRadius: 0,
              fill: false
            },
            {
              label: 'Critical Threshold (52°C)',
              data: [],
              borderColor: 'rgba(239, 68, 68, 0.6)',
              borderDash: [5, 5],
              borderWidth: 1.5,
              pointRadius: 0,
              fill: false
            }
          ]
        },
        options: this.getChartCommonOptions('Temperature (°C)', 15, 70, '°C')
      });
    }

    // 4. Live Hum Chart
    const lhCanvas = document.getElementById('liveHumChart');
    if (lhCanvas) {
      this.charts.liveHum = new Chart(lhCanvas.getContext('2d'), {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Enclosure Humidity',
              data: [],
              borderColor: '#6366F1',
              backgroundColor: 'rgba(99, 102, 241, 0.08)',
              fill: true,
              tension: 0.3,
              borderWidth: 2.5,
              pointRadius: 3
            },
            {
              label: 'Warning Limit (70%)',
              data: [],
              borderColor: 'rgba(245, 158, 11, 0.5)',
              borderDash: [5, 5],
              borderWidth: 1.5,
              pointRadius: 0,
              fill: false
            },
            {
              label: 'Critical Moisture (85%)',
              data: [],
              borderColor: 'rgba(239, 68, 68, 0.6)',
              borderDash: [5, 5],
              borderWidth: 1.5,
              pointRadius: 0,
              fill: false
            }
          ]
        },
        options: this.getChartCommonOptions('Relative Humidity (%)', 15, 100, '%')
      });
    }
  }

  setChartHistory(limit) {
    this.chartHistoryLimit = limit;
    this.fetchReadings();
    this.showToast(`Chart history window set to ${limit} points`, 'info');
  }

  // -------------------------------------------------------------
  // DATA FETCHING & LIVE POLLING LOOP
  // -------------------------------------------------------------

  startPolling() {
    if (this.pollTimer) clearInterval(this.pollTimer);
    this.pollTimer = setInterval(() => {
      this.fetchSystemStatus();
      this.fetchReadings();
      this.fetchAlerts();
    }, this.pollIntervalMs);
  }

  async fetchSystemStatus() {
    try {
      const resp = await fetch(`${this.apiBase}/status`);
      if (!resp.ok) return;
      const data = await resp.json();
      this.renderStatusPills(data);
      this.renderKPIs(data);
    } catch (err) {
      console.warn("Poll status failed:", err);
    }
  }

  renderStatusPills(statusData) {
    const hwPill = document.getElementById('top-hw-pill');
    const hwText = document.getElementById('top-hw-text');
    const modePill = document.getElementById('top-mode-pill');
    const modeText = document.getElementById('top-mode-text');
    const beacon = document.getElementById('global-beacon');
    const globalText = document.getElementById('global-status-text');

    // ESP32 Hardware Status
    if (statusData.hardware && statusData.hardware.connected) {
      hwPill.className = 'chip chip-hardware online';
      hwText.textContent = `ESP32 Online (${statusData.hardware.last_seen_seconds}s ago)`;
    } else {
      hwPill.className = 'chip chip-hardware disconnected';
      hwText.textContent = 'ESP32 Offline';
    }

    // Monitoring Mode
    const mode = statusData.monitoring_mode || 'IDLE';
    modePill.className = `chip chip-mode ${mode.toLowerCase()}`;
    modeText.textContent = `${mode} MODE`;

    // Global Status Beacon
    const unresAlerts = statusData.summary ? statusData.summary.alerts.unresolved : 0;
    if (unresAlerts > 0) {
      beacon.style.background = 'var(--status-critical)';
      beacon.style.boxShadow = '0 0 10px var(--status-critical)';
      globalText.textContent = `${unresAlerts} Active Alarm(s)`;
      globalText.style.color = 'var(--status-critical)';
    } else {
      beacon.style.background = 'var(--status-normal)';
      beacon.style.boxShadow = '0 0 8px var(--status-normal)';
      globalText.textContent = 'System Nominal';
      globalText.style.color = 'var(--text-primary)';
    }
  }

  renderKPIs(statusData) {
    const latest = statusData.latest_reading;
    if (!latest) return;

    // 1. Temperature
    const tempEl = document.getElementById('kpi-temp');
    const tempBadge = document.getElementById('kpi-temp-badge');
    if (tempEl) tempEl.textContent = latest.temperature.toFixed(1);
    
    if (tempBadge) {
      if (latest.temperature >= 52.0) {
        tempBadge.className = 'trend-badge trend-crit';
        tempBadge.textContent = 'CRITICAL';
      } else if (latest.temperature >= 38.0) {
        tempBadge.className = 'trend-badge trend-warn';
        tempBadge.textContent = 'WARNING';
      } else {
        tempBadge.className = 'trend-badge trend-normal';
        tempBadge.textContent = 'NOMINAL';
      }
    }

    // 2. Humidity
    const humEl = document.getElementById('kpi-hum');
    const humBadge = document.getElementById('kpi-hum-badge');
    if (humEl) humEl.textContent = latest.humidity.toFixed(1);

    if (humBadge) {
      if (latest.humidity >= 85.0) {
        humBadge.className = 'trend-badge trend-crit';
        humBadge.textContent = 'CRITICAL';
      } else if (latest.humidity >= 70.0) {
        humBadge.className = 'trend-badge trend-warn';
        humBadge.textContent = 'WARNING';
      } else {
        humBadge.className = 'trend-badge trend-normal';
        humBadge.textContent = 'NOMINAL';
      }
    }

    // 3. AI Score
    const aiEl = document.getElementById('kpi-ai-score');
    const aiBadge = document.getElementById('kpi-ai-badge');
    const scoreVal = latest.anomaly_score || 0.0;
    if (aiEl) aiEl.textContent = (scoreVal >= 0 ? '+' : '') + scoreVal.toFixed(3);

    if (aiBadge) {
      if (latest.is_anomaly === 1) {
        aiBadge.className = 'trend-badge trend-crit';
        aiBadge.textContent = 'ANOMALY DETECTED';
      } else {
        aiBadge.className = 'trend-badge trend-normal';
        aiBadge.textContent = 'INLIER (NORMAL)';
      }
    }

    // 4. Alerts
    const alertCountEl = document.getElementById('kpi-alerts-count');
    const alertSubEl = document.getElementById('kpi-alerts-subtext');
    const unres = statusData.summary ? statusData.summary.alerts.unresolved : 0;
    if (alertCountEl) alertCountEl.textContent = unres;
    if (alertSubEl) alertSubEl.textContent = unres > 0 ? `${unres} requires action` : 'No active hazards';

    // Quick Chart Pills
    const qTemp = document.getElementById('quick-temp-val');
    const qHum = document.getElementById('quick-hum-val');
    if (qTemp) qTemp.textContent = `${latest.temperature.toFixed(1)} °C`;
    if (qHum) qHum.textContent = `${latest.humidity.toFixed(1)} %`;

    // Last Sync timestamp
    const tsEl = document.getElementById('latest-ts');
    if (tsEl) tsEl.textContent = `Last sync: ${latest.timestamp.replace('T', ' ').substring(11, 19)} UTC`;
  }

  async fetchReadings() {
    try {
      const resp = await fetch(`${this.apiBase}/readings?limit=${this.chartHistoryLimit}&order=ASC`);
      if (!resp.ok) return;
      const data = await resp.json();
      const readings = data.readings || [];
      if (readings.length === 0) return;

      this.updateCharts(readings);
      this.updateRecentTable(readings);
      this.updateFeatureVector(readings);
    } catch (err) {
      console.warn("Fetch readings failed:", err);
    }
  }

  updateCharts(readings) {
    const labels = readings.map(r => r.timestamp.substring(11, 19));
    const temps = readings.map(r => r.temperature);
    const hums = readings.map(r => r.humidity);

    // 1. Overview Temp
    if (this.charts.overviewTemp) {
      this.charts.overviewTemp.data.labels = labels;
      this.charts.overviewTemp.data.datasets[0].data = temps;
      this.charts.overviewTemp.update('none');
    }

    // 2. Overview Hum
    if (this.charts.overviewHum) {
      this.charts.overviewHum.data.labels = labels;
      this.charts.overviewHum.data.datasets[0].data = hums;
      this.charts.overviewHum.update('none');
    }

    // 3. Live Temp (With threshold lines)
    if (this.charts.liveTemp) {
      this.charts.liveTemp.data.labels = labels;
      this.charts.liveTemp.data.datasets[0].data = temps;
      this.charts.liveTemp.data.datasets[0].rawReadings = readings;
      this.charts.liveTemp.data.datasets[1].data = labels.map(() => 38.0);
      this.charts.liveTemp.data.datasets[2].data = labels.map(() => 52.0);
      this.charts.liveTemp.update('none');
    }

    // 4. Live Hum
    if (this.charts.liveHum) {
      this.charts.liveHum.data.labels = labels;
      this.charts.liveHum.data.datasets[0].data = hums;
      this.charts.liveHum.data.datasets[1].data = labels.map(() => 70.0);
      this.charts.liveHum.data.datasets[2].data = labels.map(() => 85.0);
      this.charts.liveHum.update('none');
    }
  }

  updateRecentTable(readings) {
    const tableBody = document.getElementById('overview-recent-table');
    if (!tableBody) return;

    // Show last 6 in reverse order (newest top)
    const recent = readings.slice(-6).reverse();
    tableBody.innerHTML = recent.map(r => `
      <tr>
        <td style="font-family: var(--font-mono); font-size: 11px;">#${r.id}</td>
        <td style="font-family: var(--font-mono); font-size: 11px;">${r.timestamp.replace('T', ' ').substring(0, 19)}</td>
        <td style="font-weight: 600; color: ${r.temperature >= 38 ? '#F59E0B' : 'inherit'};">${r.temperature.toFixed(2)} °C</td>
        <td style="font-weight: 600; color: ${r.humidity >= 70 ? '#F59E0B' : 'inherit'};">${r.humidity.toFixed(2)} %</td>
        <td><span class="severity-badge ${r.source === 'HARDWARE' ? 'sev-info' : 'sev-warning'}">${r.source}</span></td>
        <td>
          <span class="severity-badge ${r.is_anomaly ? 'sev-critical' : 'sev-info'}">
            ${r.is_anomaly ? 'OUTLIER ANOMALY' : 'NORMAL INLIER'}
          </span>
        </td>
        <td style="font-family: var(--font-mono);">${r.anomaly_score >= 0 ? '+' : ''}${r.anomaly_score.toFixed(4)}</td>
      </tr>
    `).join('');
  }

  updateFeatureVector(readings) {
    if (readings.length === 0) return;
    const current = readings[readings.length - 1];
    const prev = readings.length > 1 ? readings[readings.length - 2] : current;

    const deltaT = current.temperature - prev.temperature;
    const deltaH = current.humidity - prev.humidity;

    const recentWindow = readings.slice(-5);
    const avgT = recentWindow.reduce((s, r) => s + r.temperature, 0) / recentWindow.length;
    const avgH = recentWindow.reduce((s, r) => s + r.humidity, 0) / recentWindow.length;

    // Update table elements
    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setTxt('feat-temp', `${current.temperature.toFixed(2)} °C`);
    setTxt('feat-hum', `${current.humidity.toFixed(2)} %`);
    setTxt('feat-dtemp', `${deltaT >= 0 ? '+' : ''}${deltaT.toFixed(2)} °C`);
    setTxt('feat-dhum', `${deltaH >= 0 ? '+' : ''}${deltaH.toFixed(2)} %`);
    setTxt('feat-rtemp', `${avgT.toFixed(2)} °C`);
    setTxt('feat-rhum', `${avgH.toFixed(2)} %`);

    // Decision score meter update
    const scoreMarker = document.getElementById('score-meter-marker');
    const scoreReadout = document.getElementById('ai-score-readout');
    const s = current.anomaly_score || 0.0;
    if (scoreReadout) scoreReadout.textContent = `${s >= 0 ? '+' : ''}${s.toFixed(3)}`;
    
    if (scoreMarker) {
      // Map score from approx [-0.3, +0.3] into [5%, 95%]
      const pct = Math.max(5, Math.min(95, 50 + (s * 150)));
      scoreMarker.style.left = `${pct}%`;
    }

    // Explanation Box
    const assessHeader = document.getElementById('ai-assessment-header');
    const assessText = document.getElementById('ai-assessment-text');
    const assessBox = document.getElementById('ai-explanation-box');

    if (current.is_anomaly === 1) {
      if (assessBox) {
        assessBox.style.background = 'rgba(239, 68, 68, 0.1)';
        assessBox.style.borderColor = 'rgba(239, 68, 68, 0.35)';
      }
      if (assessHeader) {
        assessHeader.style.color = 'var(--status-critical)';
        assessHeader.textContent = 'STATUS: UNUSUAL PATTERN DETECTED';
      }
      if (assessText) {
        let reasons = [];
        if (current.temperature > 38.0) reasons.push(`High thermal elevation (${current.temperature.toFixed(1)}°C)`);
        if (current.humidity > 70.0) reasons.push(`Elevated moisture levels (${current.humidity.toFixed(1)}%)`);
        if (Math.abs(deltaT) >= 3.0) reasons.push(`Thermal fluctuation of ${deltaT.toFixed(1)}°C`);
        assessText.textContent = reasons.length ? reasons.join('; ') : 'Multivariate environmental outlier signature.';
      }
    } else {
      if (assessBox) {
        assessBox.style.background = 'rgba(16, 185, 129, 0.08)';
        assessBox.style.borderColor = 'rgba(16, 185, 129, 0.25)';
      }
      if (assessHeader) {
        assessHeader.style.color = 'var(--status-normal)';
        assessHeader.textContent = 'STATUS: NOMINAL CLIMATE';
      }
      if (assessText) {
        assessText.textContent = 'Environmental conditions align with learned normal operational profile.';
      }
    }
  }

  // -------------------------------------------------------------
  // ALERTS & ANOMALIES MANAGEMENT
  // -------------------------------------------------------------

  async fetchAlerts() {
    try {
      let url = `${this.apiBase}/alerts?limit=50`;
      if (this.currentAlertFilter !== 'ALL') {
        if (this.currentAlertFilter === 'UNRESOLVED') url += '&status=UNRESOLVED';
        else url += `&severity=${this.currentAlertFilter}`;
      }

      const resp = await fetch(url);
      if (!resp.ok) return;
      const data = await resp.json();
      this.renderAlertsTable(data.alerts || []);
    } catch (err) {
      console.warn("Fetch alerts failed:", err);
    }
  }

  renderAlertsTable(alerts) {
    const tableBody = document.getElementById('alerts-table-body');
    if (!tableBody) return;

    if (alerts.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No alerts match the active filter.</td></tr>`;
      return;
    }

    tableBody.innerHTML = alerts.map(a => `
      <tr>
        <td style="font-family: var(--font-mono); font-size: 11px;">#${a.id}</td>
        <td style="font-family: var(--font-mono); font-size: 11px;">${a.timestamp.replace('T', ' ').substring(0, 19)}</td>
        <td>
          <span class="severity-badge ${a.severity === 'CRITICAL' ? 'sev-critical' : (a.severity === 'WARNING' ? 'sev-warning' : 'sev-info')}">
            ${a.severity}
          </span>
        </td>
        <td style="font-weight: 500;">${a.message}</td>
        <td style="font-size: 12px; color: var(--text-secondary);">${a.temperature ? a.temperature.toFixed(1) + '°C' : '--'} / ${a.humidity ? a.humidity.toFixed(1) + '%' : '--'}</td>
        <td>
          <span class="severity-badge ${a.status === 'UNRESOLVED' ? 'sev-critical' : 'sev-info'}">${a.status}</span>
        </td>
        <td>
          ${a.status === 'UNRESOLVED' ? `
            <button class="btn btn-secondary btn-pill" onclick="app.acknowledgeAlert(${a.id})">
              Acknowledge
            </button>
          ` : `<span style="color: var(--text-muted); font-size: 11px;">Acknowledged</span>`}
        </td>
      </tr>
    `).join('');
  }

  filterAlerts(filterType) {
    this.currentAlertFilter = filterType;
    document.querySelectorAll('#view-alerts .btn-group .btn').forEach(btn => {
      btn.classList.toggle('active', btn.textContent.trim().toUpperCase() === filterType);
    });
    this.fetchAlerts();
  }

  async acknowledgeAlert(alertId) {
    try {
      const resp = await fetch(`${this.apiBase}/alerts/${alertId}/acknowledge`, { method: 'POST' });
      if (resp.ok) {
        this.showToast(`Alert #${alertId} acknowledged`, 'success');
        this.fetchAlerts();
        this.fetchSystemStatus();
      } else {
        this.showToast(`Failed to acknowledge alert #${alertId}`, 'error');
      }
    } catch (err) {
      this.showToast(`Error: ${err.message}`, 'error');
    }
  }

  async refreshAnomalies() {
    try {
      const resp = await fetch(`${this.apiBase}/readings?anomalies_only=true&limit=50&order=DESC`);
      if (!resp.ok) return;
      const data = await resp.json();
      const anomalies = data.readings || [];
      const tableBody = document.getElementById('anomalies-table-body');
      if (!tableBody) return;

      if (anomalies.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No anomalies detected. Enclosure operating inside normal parameters.</td></tr>`;
        return;
      }

      tableBody.innerHTML = anomalies.map(r => `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 11px;">#${r.id}</td>
          <td style="font-family: var(--font-mono); font-size: 11px;">${r.timestamp.replace('T', ' ').substring(0, 19)}</td>
          <td style="font-weight: 700; color: ${r.temperature >= 38 ? '#F59E0B' : 'inherit'};">${r.temperature.toFixed(2)} °C</td>
          <td style="font-weight: 700; color: ${r.humidity >= 70 ? '#F59E0B' : 'inherit'};">${r.humidity.toFixed(2)} %</td>
          <td style="font-family: var(--font-mono); color: #EF4444;">${r.anomaly_score.toFixed(4)}</td>
          <td><span class="severity-badge sev-critical">OUTLIER ANOMALY</span></td>
          <td><span class="severity-badge sev-info">${r.source}</span></td>
        </tr>
      `).join('');
    } catch (err) {
      console.warn("Refresh anomalies failed:", err);
    }
  }

  // -------------------------------------------------------------
  // SIMULATION LAB CONTROLS
  // -------------------------------------------------------------

  selectScenario(key) {
    this.selectedScenario = key;
    document.querySelectorAll('.scenario-card').forEach(card => {
      card.classList.toggle('active', card.getAttribute('data-scenario') === key);
    });
  }

  async startSimulation() {
    const slider = document.getElementById('sim-cadence-slider');
    const interval = slider ? parseFloat(slider.value) : 1.5;

    try {
      const resp = await fetch(`${this.apiBase}/simulation/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: this.selectedScenario, interval: interval })
      });
      const data = await resp.json();

      if (resp.ok) {
        this.showToast(`Simulation started: ${this.selectedScenario.toUpperCase()} (${interval}s)`, 'success');
        this.updateSimStatusUI(true, `Running scenario: ${this.selectedScenario} at ${interval}s interval`);
      } else {
        this.showToast(`Failed: ${data.error || 'Server error'}`, 'error');
      }
    } catch (err) {
      this.showToast(`Simulation network error: ${err.message}`, 'error');
    }
  }

  async stopSimulation() {
    try {
      const resp = await fetch(`${this.apiBase}/simulation/stop`, { method: 'POST' });
      if (resp.ok) {
        this.showToast('Simulation stopped', 'info');
        this.updateSimStatusUI(false, 'Simulator stopped by operator');
      }
    } catch (err) {
      this.showToast(`Error stopping simulation: ${err.message}`, 'error');
    }
  }

  updateSimStatusUI(running, msg) {
    const badge = document.getElementById('sim-state-badge');
    const log = document.getElementById('sim-log-text');
    if (badge) {
      badge.className = `severity-badge ${running ? 'sev-info' : 'sev-warning'}`;
      badge.textContent = running ? 'RUNNING' : 'STOPPED';
    }
    if (log) log.textContent = msg;
  }

  // -------------------------------------------------------------
  // AI & ANALYTICS
  // -------------------------------------------------------------

  async fetchAIStatus() {
    try {
      const resp = await fetch(`${this.apiBase}/ai/status`);
      if (!resp.ok) return;
      const data = await resp.json();
      const ai = data.ai;

      const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
      if (ai.loaded) {
        setTxt('ai-engine-status', 'OPERATIONAL');
        setTxt('ai-trees', `${ai.n_estimators || 100} Trees`);
        setTxt('ai-contam', `${((ai.contamination || 0.05) * 100).toFixed(1)}%`);
        setTxt('ai-samples', (ai.training_samples || 11242).toLocaleString());
      }
    } catch (err) {
      console.warn("Fetch AI status failed:", err);
    }
  }

  async retrainModel() {
    const btn = document.getElementById('btn-retrain-ai');
    if (btn) btn.disabled = true;
    this.showToast("Initiating Isolation Forest retraining...", "info");

    try {
      const resp = await fetch(`${this.apiBase}/ai/train`, { method: 'POST' });
      const data = await resp.json();
      if (resp.ok) {
        this.showToast("AI Model successfully retrained & saved!", "success");
        this.fetchAIStatus();
      } else {
        this.showToast(`Retraining failed: ${data.message}`, "error");
      }
    } catch (err) {
      this.showToast(`Network error: ${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async fetchAnalytics() {
    try {
      const resp = await fetch(`${this.apiBase}/analytics`);
      if (!resp.ok) return;
      const data = await resp.json();
      const ana = data.analytics;

      const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
      setTxt('ana-total-readings', (ana.readings_count || 0).toLocaleString());
      setTxt('ana-anomaly-rate', `${ana.anomaly_rate_pct || 0}%`);
      
      const tMin = ana.temperature.min !== null ? ana.temperature.min : '--';
      const tMax = ana.temperature.max !== null ? ana.temperature.max : '--';
      setTxt('ana-temp-range', `${tMin}°C / ${tMax}°C`);

      const hMin = ana.humidity.min !== null ? ana.humidity.min : '--';
      const hMax = ana.humidity.max !== null ? ana.humidity.max : '--';
      setTxt('ana-hum-range', `${hMin}% / ${hMax}%`);
    } catch (err) {
      console.warn("Fetch analytics failed:", err);
    }
  }
}

// Instantiate global app instance
const app = new CabinetSenseApp();
window.app = app;
