/**
 * ThermoGuard AI - Frontend Controller & SCADA Application Engine
 * Manages 4-tab SPA navigation (Dashboard, History, Alerts, Settings),
 * real-time Chart.js telemetry visualization, live polling, and simulation controls.
 */

class ThermoGuardApp {
  constructor() {
    this.apiBase = "/api";
    this.pollIntervalMs = 2000;
    this.chartHistoryLimit = 25;
    this.alertFilter = "ALL";
    this.pollTimer = null;
    this.historyChart = null;
    this.cachedReadings = [];

    this.init();
  }

  init() {
    this.setupNavigation();
    this.setupSidebarToggle();
    this.setupClock();
    this.initChart();
    this.startPolling();
    this.refreshIcons();

    // Initial data fetch
    this.fetchSystemStatus();
    this.fetchLatestReading();
    this.fetchAlerts();
    this.fetchReadings();
  }

  refreshIcons() {
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  // -------------------------------------------------------------
  // 1. NAVIGATION & LAYOUT
  // -------------------------------------------------------------
  setupNavigation() {
    const navLinks = document.querySelectorAll(".nav-link");
    navLinks.forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const page = link.getAttribute("data-page");
        this.navigate(page);
      });
    });

    // Handle hash on load
    const initialHash = window.location.hash.replace("#", "");
    if (initialHash) {
      this.navigate(initialHash);
    }
  }

  navigate(pageId) {
    // Map legacy 8-view names to our modern 4-tab views
    const viewMap = {
      overview: "dashboard",
      monitoring: "dashboard",
      "ai-center": "dashboard",
      anomalies: "alerts",
      alerts: "alerts",
      analytics: "history",
      history: "history",
      simulation: "settings",
      settings: "settings",
      dashboard: "dashboard",
    };

    const targetView = viewMap[pageId] || "dashboard";

    // Update active nav link
    document.querySelectorAll(".nav-link").forEach((link) => {
      const page = link.getAttribute("data-page");
      link.classList.toggle("active", page === targetView);
    });

    // Update active view section
    document.querySelectorAll(".page-view").forEach((view) => {
      view.classList.toggle("active", view.id === `view-${targetView}`);
    });

    // Update page header
    const titleMap = {
      dashboard: {
        title: "Operational Dashboard",
        desc: "Real-time thermal & humidity telemetry with AI anomaly surveillance",
      },
      history: {
        title: "Telemetry History & Export",
        desc: "Historical records, sensory origins, and CSV telemetry exports",
      },
      alerts: {
        title: "SCADA Alarm & Alert Desk",
        desc: "Real-time fault tracking, temperature breaches, and alert resolution",
      },
      settings: {
        title: "System & Hardware Settings",
        desc: "ESP32 node setup, GPIO pinout reference, and AI diagnostics",
      },
    };

    const meta = titleMap[targetView] || titleMap.dashboard;
    const titleEl = document.getElementById("current-page-title");
    const descEl = document.getElementById("current-page-desc");
    if (titleEl) titleEl.textContent = meta.title;
    if (descEl) descEl.textContent = meta.desc;

    // Refresh icons and resize chart if returning to dashboard
    this.refreshIcons();
    if (targetView === "dashboard" && this.historyChart) {
      setTimeout(() => this.historyChart.resize(), 100);
    }
    if (targetView === "history") {
      this.fetchReadings();
    }
    if (targetView === "alerts") {
      this.fetchAlerts();
    }
  }

  setupSidebarToggle() {
    const toggleBtn = document.getElementById("sidebar-toggle");
    const sidebar = document.getElementById("sidebar");
    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("collapsed");
        if (this.historyChart) {
          setTimeout(() => this.historyChart.resize(), 300);
        }
      });
    }
  }

  setupClock() {
    const updateTime = () => {
      const now = new Date();
      const timeStr = now.toISOString().slice(11, 19) + " UTC";
      const clockEl = document.getElementById("live-clock");
      const sideTimeEl = document.getElementById("sidebar-time");
      if (clockEl) clockEl.textContent = timeStr;
      if (sideTimeEl) sideTimeEl.textContent = timeStr;
    };
    updateTime();
    setInterval(updateTime, 1000);
  }

  // -------------------------------------------------------------
  // 2. CHART.JS HISTORICAL VISUALIZATION
  // -------------------------------------------------------------
  initChart() {
    const canvas = document.getElementById("mainHistoryChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    // Industrial Dark Navy Gradients
    const tempGrad = ctx.createLinearGradient(0, 0, 0, 300);
    tempGrad.addColorStop(0, "rgba(56, 189, 248, 0.35)");
    tempGrad.addColorStop(1, "rgba(56, 189, 248, 0.0)");

    const humGrad = ctx.createLinearGradient(0, 0, 0, 300);
    humGrad.addColorStop(0, "rgba(129, 140, 248, 0.3)");
    humGrad.addColorStop(1, "rgba(129, 140, 248, 0.0)");

    this.historyChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Temperature (°C)",
            data: [],
            borderColor: "#38BDF8",
            backgroundColor: tempGrad,
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: "#38BDF8",
            yAxisID: "yTemp",
          },
          {
            label: "Humidity (%)",
            data: [],
            borderColor: "#818CF8",
            backgroundColor: humGrad,
            borderWidth: 2,
            borderDash: [4, 4],
            fill: false,
            tension: 0.35,
            pointRadius: 2,
            pointHoverRadius: 5,
            pointBackgroundColor: "#818CF8",
            yAxisID: "yHum",
          },
          {
            // Anomaly overlay — red dots plotted on the temp axis at anomaly positions
            label: "Anomaly",
            data: [],
            borderColor: "transparent",
            backgroundColor: "transparent",
            pointRadius: 7,
            pointHoverRadius: 9,
            pointBackgroundColor: "#F43F5E",
            pointBorderColor: "#FFFFFF",
            pointBorderWidth: 1.5,
            showLine: false,
            yAxisID: "yTemp",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0F172A",
            titleColor: "#F8FAFC",
            bodyColor: "#94A3B8",
            borderColor: "#1E293B",
            borderWidth: 1,
            padding: 10,
            displayColors: true,
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(30, 41, 59, 0.5)", drawBorder: false },
            ticks: { color: "#64748B", font: { size: 11, family: "JetBrains Mono" }, maxRotation: 0 },
          },
          yTemp: {
            type: "linear",
            position: "left",
            min: 10,
            max: 70,
            title: { display: true, text: "Temperature (°C)", color: "#38BDF8", font: { size: 11, weight: "bold" } },
            grid: { color: "rgba(30, 41, 59, 0.6)" },
            ticks: { color: "#94A3B8", font: { size: 11, family: "JetBrains Mono" }, stepSize: 10 },
          },
          yHum: {
            type: "linear",
            position: "right",
            min: 0,
            max: 100,
            title: { display: true, text: "Humidity (%)", color: "#818CF8", font: { size: 11, weight: "bold" } },
            grid: { drawOnChartArea: false },
            ticks: { color: "#94A3B8", font: { size: 11, family: "JetBrains Mono" }, stepSize: 20 },
          },
        },
      },
    });
  }

  updateChartData(readings) {
    if (!this.historyChart || !readings || !readings.length) return;

    // Take the most recent items in ascending chronological order
    const slice = [...readings].reverse().slice(-this.chartHistoryLimit);

    const labels = slice.map((r) => {
      const dt = new Date(r.timestamp);
      return dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    });

    const temps = slice.map((r) => r.temperature);
    const hums = slice.map((r) => r.humidity);
    // Red dot at the temperature value for anomalies, null (hidden) for normal readings
    const anomalyDots = slice.map((r) => (r.is_anomaly ? r.temperature : null));

    this.historyChart.data.labels = labels;
    this.historyChart.data.datasets[0].data = temps;
    this.historyChart.data.datasets[1].data = hums;
    this.historyChart.data.datasets[2].data = anomalyDots;
    this.historyChart.update("none");
  }

  // -------------------------------------------------------------
  // 3. LIVE POLLING & API CONSUMPTION
  // -------------------------------------------------------------
  startPolling() {
    this.stopPolling();
    this.pollTimer = setInterval(() => {
      this.fetchSystemStatus();
      this.fetchLatestReading();
      this.fetchAlerts();
      this.fetchReadings(); // keep chart + anomaly dots live
    }, this.pollIntervalMs);
  }

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  async fetchSystemStatus() {
    try {
      const res = await fetch(`${this.apiBase}/status`);
      if (!res.ok) throw new Error("Status check failed");
      const data = await res.json();
      this.renderSystemStatus(data);
    } catch {
      this.renderSystemOffline();
    }
  }

  renderSystemStatus(data) {
    const isOnline = data != null && data.monitoring_mode != null;
    const hwConnected = data && data.hardware && data.hardware.connected;
    const hwStatus = (data && data.hardware) || {};

    // KPI System Status card
    const kpiStatus = document.getElementById("kpi-system-status");
    if (kpiStatus) {
      kpiStatus.textContent = isOnline ? "ONLINE" : "OFFLINE";
      kpiStatus.className = isOnline ? "kpi-value text-emerald" : "kpi-value text-rose";
    }
    const kpiHwBadge = document.getElementById("kpi-hw-badge");
    if (kpiHwBadge) {
      kpiHwBadge.textContent = hwConnected ? "ESP32 Active" : "Awaiting Sensor";
      kpiHwBadge.className = hwConnected ? "badge badge-normal" : "badge badge-warning";
    }

    // Global Topbar Pills
    const topHwPill = document.getElementById("top-hw-pill");
    const topHwText = document.getElementById("top-hw-text");
    if (topHwPill && topHwText) {
      topHwPill.className = `chip chip-hardware ${hwConnected ? "connected" : "disconnected"}`;
      topHwText.textContent = hwConnected ? "ESP32 Online (GPIO 4)" : "ESP32 Offline";
    }

    const topModePill = document.getElementById("top-mode-pill");
    const topModeText = document.getElementById("top-mode-text");
    if (topModePill && topModeText) {
      topModeText.textContent = hwConnected ? "HARDWARE LIVE" : "STANDBY";
    }

    // Hero Banner
    const beaconEl = document.getElementById("hero-beacon");
    const titleEl = document.getElementById("hero-title");
    const descEl = document.getElementById("hero-desc");
    const globalBeacon = document.getElementById("global-beacon");
    const globalStatusText = document.getElementById("global-status-text");

    if (isOnline) {
      if (beaconEl) beaconEl.className = "hero-beacon-circle online";
      if (titleEl) titleEl.textContent = "System Status: ONLINE";
      if (globalBeacon) globalBeacon.className = "status-beacon pulse online";
      if (globalStatusText) globalStatusText.textContent = "System Online";

      if (descEl) {
        if (hwConnected) {
          descEl.textContent = "Live physical sensor telemetry streaming from ESP32 on GPIO 4. AI anomaly detection active.";
        } else {
          descEl.textContent = "ThermoGuard AI operational. Awaiting incoming physical sensor packets from ESP32 on /api/readings.";
        }
      }
    }

    // Quick Hardware Status
    const quickDot = document.getElementById("quick-hw-dot");
    const quickText = document.getElementById("quick-hw-text");
    if (quickDot && quickText) {
      quickDot.className = `dot ${hwConnected ? "connected" : ""}`;
      quickText.textContent = hwConnected
        ? "ESP32 Hardware connected & streaming telemetry!"
        : "ESP32 Hardware: Listening for packets on /api/readings";
    }

    // Hardware Node telemetry monitor card
    const hwNodeBadge = document.getElementById("hw-node-badge");
    const hwClientIp = document.getElementById("hw-client-ip");
    const hwLastSeen = document.getElementById("hw-last-seen");

    if (hwNodeBadge) {
      hwNodeBadge.textContent = hwConnected ? "Online" : "Awaiting Sensor";
      hwNodeBadge.className = hwConnected ? "badge badge-normal" : "badge badge-warning";
    }
    if (hwClientIp) {
      hwClientIp.textContent = hwStatus.client_ip || "None (Offline)";
    }
    if (hwLastSeen) {
      hwLastSeen.textContent =
        hwStatus.last_seen_seconds != null ? `${hwStatus.last_seen_seconds}s ago` : "Never";
    }

    // 24-Hour Statistics Panel update
    if (data && data.summary_24h) {
      this.render24hStats(data.summary_24h);
    }
  }

  render24hStats(stats) {
    if (!stats) return;

    // Ingested readings count badge
    const badgePoints = document.getElementById("badge-24h-points");
    if (badgePoints) {
      badgePoints.textContent = `${stats.readings_count || 0} Readings (24h)`;
    }

    // Temperature (min, max, avg)
    const t = stats.temperature || {};
    const tMinEl = document.getElementById("stat-temp-min");
    const tMaxEl = document.getElementById("stat-temp-max");
    const tAvgEl = document.getElementById("stat-temp-avg");
    const tEvalEl = document.getElementById("stat-temp-eval");
    const tFillEl = document.getElementById("stat-temp-fill");

    if (tAvgEl) tAvgEl.textContent = t.avg != null ? t.avg.toFixed(1) : "--.-";
    if (tMinEl) tMinEl.textContent = t.min != null ? `${t.min.toFixed(1)}°C` : "--.-°C";
    if (tMaxEl) tMaxEl.textContent = t.max != null ? `${t.max.toFixed(1)}°C` : "--.-°C";

    if (tEvalEl) {
      const maxT = t.max || 0;
      if (maxT >= 52.0) {
        tEvalEl.textContent = "Critical Limit";
        tEvalEl.className = "badge badge-critical";
      } else if (maxT >= 38.0) {
        tEvalEl.textContent = "Elevated";
        tEvalEl.className = "badge badge-warning";
      } else {
        tEvalEl.textContent = "Nominal";
        tEvalEl.className = "badge badge-normal";
      }
    }

    if (tFillEl && t.avg != null) {
      const pct = Math.max(5, Math.min(100, ((t.avg - 10) / 60) * 100));
      tFillEl.style.width = `${pct}%`;
    }

    // Humidity (min, max, avg)
    const h = stats.humidity || {};
    const hMinEl = document.getElementById("stat-hum-min");
    const hMaxEl = document.getElementById("stat-hum-max");
    const hAvgEl = document.getElementById("stat-hum-avg");
    const hEvalEl = document.getElementById("stat-hum-eval");
    const hFillEl = document.getElementById("stat-hum-fill");

    if (hAvgEl) hAvgEl.textContent = h.avg != null ? h.avg.toFixed(1) : "--.-";
    if (hMinEl) hMinEl.textContent = h.min != null ? `${h.min.toFixed(1)}%` : "--.-%";
    if (hMaxEl) hMaxEl.textContent = h.max != null ? `${h.max.toFixed(1)}%` : "--.-%";

    if (hEvalEl) {
      const maxH = h.max || 0;
      if (maxH >= 85.0) {
        hEvalEl.textContent = "Critical Moisture";
        hEvalEl.className = "badge badge-critical";
      } else if (maxH >= 70.0) {
        hEvalEl.textContent = "High Humidity";
        hEvalEl.className = "badge badge-warning";
      } else {
        hEvalEl.textContent = "Nominal";
        hEvalEl.className = "badge badge-normal";
      }
    }

    if (hFillEl && h.avg != null) {
      const pct = Math.max(5, Math.min(100, h.avg));
      hFillEl.style.width = `${pct}%`;
    }

    // AI Anomaly Rate
    const anomCount = stats.anomalies_count || 0;
    const readCount = stats.readings_count || 0;
    const anomRate = stats.anomaly_rate_pct != null ? stats.anomaly_rate_pct.toFixed(1) : "0.0";
    const nominalCount = Math.max(0, readCount - anomCount);

    const anomRateEl = document.getElementById("stat-anomaly-rate");
    const anomCountEl = document.getElementById("stat-anomaly-count");
    const nomCountEl = document.getElementById("stat-nominal-count");
    const anomEvalEl = document.getElementById("stat-anomaly-eval");

    if (anomRateEl) {
      anomRateEl.textContent = anomRate;
      anomRateEl.className = anomCount > 0 ? "stat-avg text-rose" : "stat-avg text-emerald";
    }
    if (anomCountEl) anomCountEl.textContent = anomCount;
    if (nomCountEl) nomCountEl.textContent = nominalCount;
    if (anomEvalEl) {
      if (anomCount > 5) {
        anomEvalEl.textContent = "High Ingress";
        anomEvalEl.className = "badge badge-critical";
      } else if (anomCount > 0) {
        anomEvalEl.textContent = "Anomalies Seen";
        anomEvalEl.className = "badge badge-warning";
      } else {
        anomEvalEl.textContent = "Clean";
        anomEvalEl.className = "badge badge-normal";
      }
    }

    // Alerts Breakdown
    const alerts = stats.alerts || {};
    const alertTotalEl = document.getElementById("stat-alerts-total");
    const alertCritEl = document.getElementById("stat-alert-crit");
    const alertWarnEl = document.getElementById("stat-alert-warn");
    const alertUnresEl = document.getElementById("stat-alert-unres");

    if (alertTotalEl) alertTotalEl.textContent = `${alerts.total || 0} Alarms (24h)`;
    if (alertCritEl) alertCritEl.textContent = alerts.critical || 0;
    if (alertWarnEl) alertWarnEl.textContent = alerts.warning || 0;
    if (alertUnresEl) alertUnresEl.textContent = alerts.unresolved || 0;
  }

  renderSystemOffline() {
    const beaconEl = document.getElementById("hero-beacon");
    const titleEl = document.getElementById("hero-title");
    const descEl = document.getElementById("hero-desc");
    const globalBeacon = document.getElementById("global-beacon");
    const globalStatusText = document.getElementById("global-status-text");

    if (beaconEl) beaconEl.className = "hero-beacon-circle offline";
    if (titleEl) titleEl.textContent = "System Status: OFFLINE";
    if (descEl) descEl.textContent = "Backend server unreachable. Please verify Flask server is running on port 5000.";
    if (globalBeacon) globalBeacon.className = "status-beacon offline";
    if (globalStatusText) globalStatusText.textContent = "Server Offline";
  }

  async fetchLatestReading() {
    try {
      const res = await fetch(`${this.apiBase}/readings/latest`);
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.reading) {
        this.renderLatestReading(data.reading);
      }
    } catch {
      // Polling network drop handled gracefully
    }
  }

  renderLatestReading(reading) {
    const temp = reading.temperature;
    const hum = reading.humidity;
    const isAnomaly = reading.is_anomaly === 1;
    const score = reading.anomaly_score !== undefined ? reading.anomaly_score : 0;
    const source = reading.source || "UNKNOWN";

    // Hero Info
    const heroTime = document.getElementById("hero-last-time");
    const heroSource = document.getElementById("hero-source");
    if (heroTime) {
      const d = new Date(reading.timestamp);
      heroTime.textContent = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }
    if (heroSource) heroSource.textContent = source;

    // 1. Temperature Card
    const tempVal = document.getElementById("kpi-temp-val");
    const tempStatus = document.getElementById("kpi-temp-status");
    if (tempVal) tempVal.textContent = temp.toFixed(1);
    if (tempStatus) {
      if (temp >= 52.0) {
        tempStatus.className = "badge badge-critical";
        tempStatus.textContent = "Critical Overheat";
      } else if (temp >= 38.0) {
        tempStatus.className = "badge badge-warning";
        tempStatus.textContent = "Warning Elevated";
      } else {
        tempStatus.className = "badge badge-normal";
        tempStatus.textContent = "Nominal";
      }
    }

    // 2. Humidity Card
    const humVal = document.getElementById("kpi-hum-val");
    const humStatus = document.getElementById("kpi-hum-status");
    if (humVal) humVal.textContent = hum.toFixed(1);
    if (humStatus) {
      if (hum >= 85.0) {
        humStatus.className = "badge badge-critical";
        humStatus.textContent = "Critical Ingress";
      } else if (hum >= 70.0) {
        humStatus.className = "badge badge-warning";
        humStatus.textContent = "Warning High";
      } else {
        humStatus.className = "badge badge-normal";
        humStatus.textContent = "Nominal";
      }
    }

    // 3. AI Anomaly Card
    const aiStatus = document.getElementById("kpi-ai-status");
    const aiBadge = document.getElementById("kpi-ai-badge");
    if (aiStatus) {
      aiStatus.textContent = isAnomaly ? "ANOMALY DETECTED" : "NORMAL";
      aiStatus.className = isAnomaly ? "kpi-value text-rose" : "kpi-value text-emerald";
    }
    if (aiBadge) {
      aiBadge.className = isAnomaly ? "badge badge-critical" : "badge badge-normal";
      aiBadge.textContent = `Score: ${score.toFixed(3)}`;
    }
  }

  // -------------------------------------------------------------
  // 4. TELEMETRY LOGS & HISTORY
  // -------------------------------------------------------------
  async fetchReadings() {
    try {
      const res = await fetch(`${this.apiBase}/readings?limit=50`);
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.readings) {
        this.cachedReadings = data.readings;
        this.updateChartData(data.readings);
        this.renderHistoryTable(data.readings);
      }
    } catch (err) {
      console.warn("Failed to fetch historical readings:", err);
    }
  }

  filterHistory() {
    const filterEl = document.getElementById("history-source-filter");
    const filter = filterEl ? filterEl.value : "ALL";

    let filtered = this.cachedReadings;
    if (filter === "HARDWARE") {
      filtered = this.cachedReadings.filter((r) => r.source === "HARDWARE");
    } else if (filter === "ANOMALY") {
      filtered = this.cachedReadings.filter((r) => r.is_anomaly === 1);
    }

    this.renderHistoryTable(filtered);
  }

  renderHistoryTable(readings) {
    const tbody = document.getElementById("history-tbody");
    if (!tbody) return;

    if (!readings || readings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No telemetry records match the current filter.</td></tr>`;
      return;
    }

    tbody.innerHTML = readings
      .slice(0, 50)
      .map((r) => {
        const isAnomaly = r.is_anomaly === 1;
        const anomalyBadge = isAnomaly
          ? `<span class="badge badge-critical">ANOMALY</span>`
          : `<span class="badge badge-normal">NOMINAL</span>`;

        const sourceBadge =
          r.source === "HARDWARE"
            ? `<span class="badge badge-normal">HARDWARE</span>`
            : `<span class="badge badge-purple">SIMULATION</span>`;

        return `
          <tr>
            <td><code>#${r.id}</code></td>
            <td style="font-family: var(--font-mono); font-size: 12px;">${r.timestamp}</td>
            <td><strong>${r.temperature.toFixed(2)} °C</strong></td>
            <td><strong>${r.humidity.toFixed(2)} %</strong></td>
            <td>${sourceBadge}</td>
            <td>${anomalyBadge}</td>
            <td><code>${(r.anomaly_score || 0).toFixed(4)}</code></td>
          </tr>
        `;
      })
      .join("");
  }

  // -------------------------------------------------------------
  // 5. ALERTS CENTER
  // -------------------------------------------------------------
  async fetchAlerts() {
    try {
      const res = await fetch(`${this.apiBase}/alerts?limit=50`);
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.alerts) {
        this.renderAlerts(data.alerts);
      }
    } catch (err) {
      console.warn("Failed to fetch alerts:", err);
    }
  }

  setAlertFilter(filter) {
    this.alertFilter = filter;
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-filter") === filter);
    });
    this.fetchAlerts();
  }

  renderAlerts(alerts) {
    const unresolvedCount = alerts.filter((a) => a.status === "UNRESOLVED").length;
    const badgeEl = document.getElementById("nav-alert-count");
    if (badgeEl) {
      badgeEl.textContent = unresolvedCount;
      badgeEl.style.display = unresolvedCount > 0 ? "inline-block" : "none";
    }

    // 1. Dashboard Recent Alerts Table (Top 5)
    const dashTbody = document.getElementById("dashboard-alerts-tbody");
    if (dashTbody) {
      const recent = alerts.slice(0, 5);
      if (recent.length === 0) {
        dashTbody.innerHTML = `<tr><td colspan="5" class="empty-state">No recent alerts. System operating normally.</td></tr>`;
      } else {
        dashTbody.innerHTML = recent
          .map((a) => {
            const sevBadge = this.getSeverityBadge(a.severity);
            const ackBtn =
              a.status === "UNRESOLVED"
                ? `<button class="btn btn-xs btn-outline" onclick="app.acknowledgeAlert(${a.id})">Acknowledge</button>`
                : `<span class="badge badge-normal"><i data-lucide="check"></i> Ack</span>`;

            return `
              <tr>
                <td style="font-family: var(--font-mono); font-size: 11px;">${this.formatTime(a.timestamp)}</td>
                <td>${sevBadge}</td>
                <td style="font-size: 12px; font-weight: 500;">${a.message}</td>
                <td style="font-family: var(--font-mono); font-size: 12px;">${a.temperature ?? "--"}°C / ${a.humidity ?? "--"}%</td>
                <td>${ackBtn}</td>
              </tr>
            `;
          })
          .join("");
        this.refreshIcons();
      }
    }

    // 2. Dedicated Alerts Page Table
    const alertsTbody = document.getElementById("alerts-tbody");
    if (alertsTbody) {
      let filtered = alerts;
      if (this.alertFilter === "UNRESOLVED") {
        filtered = alerts.filter((a) => a.status === "UNRESOLVED");
      } else if (this.alertFilter === "CRITICAL") {
        filtered = alerts.filter((a) => a.severity === "CRITICAL");
      } else if (this.alertFilter === "WARNING") {
        filtered = alerts.filter((a) => a.severity === "WARNING");
      }

      if (filtered.length === 0) {
        alertsTbody.innerHTML = `<tr><td colspan="8" class="empty-state">No alerts match filter '${this.alertFilter}'.</td></tr>`;
        return;
      }

      alertsTbody.innerHTML = filtered
        .map((a) => {
          const sevBadge = this.getSeverityBadge(a.severity);
          const statusBadge =
            a.status === "UNRESOLVED"
              ? `<span class="badge badge-critical">UNRESOLVED</span>`
              : `<span class="badge badge-normal">ACKNOWLEDGED</span>`;

          const ackAction =
            a.status === "UNRESOLVED"
              ? `<button class="btn btn-xs btn-primary" onclick="app.acknowledgeAlert(${a.id})">Acknowledge</button>`
              : `<span class="text-muted" style="font-size: 11px;">Resolved</span>`;

          return `
            <tr>
              <td><code>#${a.id}</code></td>
              <td style="font-family: var(--font-mono); font-size: 12px;">${a.timestamp}</td>
              <td>${sevBadge}</td>
              <td style="font-weight: 500;">${a.message}</td>
              <td><code>${a.temperature ?? "--"}°C | ${a.humidity ?? "--"}%</code></td>
              <td><code>${(a.anomaly_score || 0).toFixed(4)}</code></td>
              <td>${statusBadge}</td>
              <td>${ackAction}</td>
            </tr>
          `;
        })
        .join("");
    }
  }

  getSeverityBadge(severity) {
    if (severity === "CRITICAL") {
      return `<span class="badge badge-critical">CRITICAL</span>`;
    } else if (severity === "WARNING") {
      return `<span class="badge badge-warning">WARNING</span>`;
    }
    return `<span class="badge badge-normal">INFO</span>`;
  }

  formatTime(isoStr) {
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return isoStr;
    }
  }

  async acknowledgeAlert(alertId) {
    try {
      const res = await fetch(`${this.apiBase}/alerts/${alertId}/acknowledge`, { method: "POST" });
      if (res.ok) {
        this.showToast(`Alert #${alertId} acknowledged`, "success");
        this.fetchAlerts();
      } else {
        this.showToast(`Failed to acknowledge alert #${alertId}`, "error");
      }
    } catch (err) {
      this.showToast("Network error acknowledging alert", "error");
    }
  }

  async acknowledgeAllAlerts() {
    try {
      const res = await fetch(`${this.apiBase}/alerts/acknowledge-all`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        const count = data.count || 0;
        if (count > 0) {
          this.showToast(`Acknowledged ${count} alerts`, "success");
        } else {
          this.showToast("No unresolved alerts to acknowledge", "info");
        }
        this.fetchAlerts();
        this.fetchSystemStatus();
      } else {
        this.showToast("Failed to acknowledge all alerts", "error");
      }
    } catch (err) {
      this.showToast("Network error acknowledging alerts", "error");
    }
  }

  // -------------------------------------------------------------
  // 6. HARDWARE ENDPOINT & HELPERS
  // -------------------------------------------------------------
  copyEndpointUrl() {
    const host = window.location.hostname || "127.0.0.1";
    const port = window.location.port ? `:${window.location.port}` : ":5000";
    const url = `${window.location.protocol}//${host}${port}/api/readings`;
    navigator.clipboard
      .writeText(url)
      .then(() => this.showToast("Ingestion URL copied: " + url, "success"))
      .catch(() => this.showToast("Copy failed, please copy manually: " + url, "warning"));
  }

  copyInputUrl(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.select();
    navigator.clipboard
      .writeText(input.value)
      .then(() => this.showToast("Endpoint URL copied to clipboard!", "success"))
      .catch(() => this.showToast("Copy failed", "warning"));
  }

  // -------------------------------------------------------------
  // 7. TOAST NOTIFICATIONS
  // -------------------------------------------------------------
  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }
}

// Instantiate ThermoGuard AI frontend application
let app = null;
document.addEventListener("DOMContentLoaded", () => {
  app = new ThermoGuardApp();
  window.app = app;
  // Maintain backward compatibility for test suites
  window.CabinetSenseApp = ThermoGuardApp;
});
