// Global configurations
const MAX_CHART_POINTS = 15;
let cpuChart, memChart;
let cpuHistory = [];
let memHistory = [];
let chartLabels = [];

// Initialize History Data
for (let i = 0; i < MAX_CHART_POINTS; i++) {
    cpuHistory.push(0);
    memHistory.push(0);
    chartLabels.push("");
}

// Chart.js helper to create premium line charts
function createTelemetryChart(ctx, label, colorGradStart, colorGradStop) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 180);
    gradient.addColorStop(0, colorGradStart);
    gradient.addColorStop(1, colorGradStop);

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [{
                label: label,
                data: label === 'CPU' ? cpuHistory : memHistory,
                borderColor: colorGradStart,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: true,
                backgroundColor: gradient,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(11, 15, 25, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#f3f4f6',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1
                }
            },
            scales: {
                x: { display: false },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#9ca3af', font: { size: 9 } }
                }
            }
        }
    });
}

// Format duration
function formatUptime(seconds) {
    seconds = Math.floor(seconds);
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    let parts = [];
    if (hrs > 0) parts.push(`${hrs}h`);
    if (mins > 0) parts.push(`${mins}m`);
    parts.push(`${secs}s`);
    return "Uptime: " + parts.join(" ");
}

// Format bytes
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Update DOM elements with metrics payload
function updateDashboard(data) {
    // 1. Connection / OS Metadata
    document.getElementById("os-text").textContent = `${data.os.os_name} (${data.os.architecture})`;
    document.getElementById("uptime-text").textContent = formatUptime(data.os.uptime_seconds);

    // 2. Health score ring rendering
    const score = data.health.score;
    const status = data.health.status;
    const scoreEl = document.getElementById("health-score");
    const statusEl = document.getElementById("health-status");
    const ringEl = document.getElementById("health-ring");

    scoreEl.textContent = Math.round(score);
    statusEl.textContent = status;

    // SVG dashoffset animation (radius=70, circumference=439.8)
    const circumference = 439.8;
    const offset = circumference - (circumference * score / 100);
    ringEl.style.strokeDashoffset = offset;

    // Set colors according to status
    let statusColor, statusGlow;
    if (status === "Healthy") {
        statusColor = "var(--color-healthy)";
        statusGlow = "var(--color-healthy-glow)";
        statusEl.style.color = "var(--color-healthy)";
    } else if (status === "Degraded") {
        statusColor = "var(--color-degraded)";
        statusGlow = "var(--color-degraded-glow)";
        statusEl.style.color = "var(--color-degraded)";
    } else {
        statusColor = "var(--color-critical)";
        statusGlow = "var(--color-critical-glow)";
        statusEl.style.color = "var(--color-critical)";
    }
    ringEl.style.stroke = statusColor;
    document.getElementById("health-ring").style.filter = `drop-shadow(0 0 8px ${statusColor})`;

    // 3. CPU Card
    const cpuUsage = data.cpu.usage_percent;
    document.getElementById("cpu-subtitle").textContent = `${data.cpu.logical_cores} Cores @ ${data.cpu.frequency_mhz_current.toFixed(0)} MHz`;
    document.getElementById("cpu-val-text").textContent = `${cpuUsage.toFixed(1)}%`;
    document.getElementById("cpu-bar").style.width = `${cpuUsage}%`;
    
    // Add point to chart
    cpuHistory.push(cpuUsage);
    cpuHistory.shift();
    cpuChart.update();

    // 4. Memory Card
    const memUsage = data.memory.usage_percent;
    const memUsedStr = formatBytes(data.memory.used_bytes);
    const memTotalStr = formatBytes(data.memory.total_bytes);
    document.getElementById("mem-subtitle").textContent = `${memUsedStr} / ${memTotalStr}`;
    document.getElementById("mem-val-text").textContent = `${memUsage.toFixed(1)}%`;
    document.getElementById("mem-bar").style.width = `${memUsage}%`;

    // Add point to chart
    memHistory.push(memUsage);
    memHistory.shift();
    memChart.update();

    // 5. Storage Partitions
    const partitionsContainer = document.getElementById("disk-partitions-container");
    partitionsContainer.innerHTML = "";
    data.disk.partitions.forEach(part => {
        const usedStr = formatBytes(part.used_bytes);
        const totalStr = formatBytes(part.total_bytes);
        
        const partRow = document.createElement("div");
        partRow.className = "metric-progress-container";
        partRow.innerHTML = `
            <div class="metric-label-row">
                <span>Disk ${part.mountpoint} (${part.fstype})</span>
                <span>${part.usage_percent}%</span>
            </div>
            <div class="metric-bar-outer" style="margin-bottom:0.25rem;">
                <div class="metric-bar-inner" style="width: ${part.usage_percent}%; background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);"></div>
            </div>
            <div class="metric-label-row" style="font-size: 0.75rem; color: var(--text-secondary);">
                <span>Used: ${usedStr}</span>
                <span>Total: ${totalStr}</span>
            </div>
        `;
        partitionsContainer.appendChild(partRow);
    });

    // Disk I/O Rates
    // Get rates from baseline history
    let readSpeed = 0;
    let writeSpeed = 0;
    if (data.baseline_stats) {
        // Fallback calculation or direct rates if available from history
        if (data.baseline_stats.disk_read_rate) {
            // Read rate from baseline history is computed. Let's see if we have history points
            const len = data.baseline_stats.disk_read_rate.mean;
            // Let's show current rates computed from the last 2 seconds.
            // For now, we will display rates computed by baseline logic
        }
    }
    // We can also calculate standard difference or simulate gracefully
    // Let's write current read/write rate
    const readEl = document.getElementById("disk-read-speed");
    const writeEl = document.getElementById("disk-write-speed");
    
    // We can calculate I/O speed if we track it or read from anomalies/baseline.
    // Let's extract rates computed in backend or check if history exists.
    // If not, we fall back to a nice formatting of raw rates or delta.
    // Let's check:
    const readBytes = data.disk.read_bytes || 0;
    const writeBytes = data.disk.write_bytes || 0;
    
    if (window.lastReadBytes && window.lastTimestamp) {
        const dt = (data.timestamp - window.lastTimestamp);
        if (dt > 0) {
            const rSpeedBytes = Math.max(0, (readBytes - window.lastReadBytes) / dt);
            const wSpeedBytes = Math.max(0, (writeBytes - window.lastWriteBytes) / dt);
            readEl.textContent = `${(rSpeedBytes / 1024 / 1024).toFixed(2)} MB/s`;
            writeEl.textContent = `${(wSpeedBytes / 1024 / 1024).toFixed(2)} MB/s`;
        }
    }
    window.lastReadBytes = readBytes;
    window.lastWriteBytes = writeBytes;
    window.lastTimestamp = data.timestamp;

    // 6. Process Snapshot
    const procTableBody = document.getElementById("process-table-body");
    procTableBody.innerHTML = "";
    data.processes.forEach(proc => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td style="color:#60a5fa; font-weight:600;">${proc.pid}</td>
            <td style="font-weight:500;">${proc.name}</td>
            <td><span class="badge badge-cpu">${proc.cpu_percent}%</span></td>
            <td><span class="badge badge-mem">${proc.memory_percent}%</span></td>
            <td>${proc.status}</td>
            <td style="color:var(--text-secondary);">${proc.username}</td>
        `;
        procTableBody.appendChild(tr);
    });

    // 7. Plugin Data
    const pluginsContainer = document.getElementById("plugins-container");
    pluginsContainer.innerHTML = "";
    const pData = data.plugins_data || {};
    
    if (Object.keys(pData).length === 0) {
        pluginsContainer.innerHTML = `
            <div class="plugin-mini-card" style="grid-column: span 2; text-align: center; color: var(--text-secondary);">
                No active plugins loaded.
            </div>
        `;
    } else {
        for (const [pName, pVal] of Object.entries(pData)) {
            const card = document.createElement("div");
            card.className = "plugin-mini-card";
            
            // Format nice human-friendly plugin name
            const displayName = pName.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
            
            let contentHtml = `<div class="plugin-title">${displayName}</div>`;
            if (pVal.available) {
                if (pName === "battery_health") {
                    const chargingStr = pVal.power_plugged ? "Charging" : "Discharging";
                    contentHtml += `
                        <div class="plugin-metric"><span>Level:</span><span style="font-weight:600; color:#10b981;">${pVal.percent}%</span></div>
                        <div class="plugin-metric"><span>State:</span><span>${chargingStr}</span></div>
                    `;
                } else if (pName === "gpu_analyzer") {
                    const simTag = pVal.simulated ? ' <span style="font-size:0.75rem; color:#f59e0b;">(sim)</span>' : '';
                    contentHtml += `
                        <div class="plugin-metric"><span>GPU Load:</span><span style="font-weight:600; color:#60a5fa;">${pVal.utilization_gpu_percent}%</span></div>
                        <div class="plugin-metric"><span>Temp:</span><span>${pVal.temperature_c}°C</span></div>
                        <div class="plugin-metric" style="font-size:0.75rem; color:var(--text-secondary);"><span>Device:</span><span>${pVal.gpu_name.replace("(Simulated)", "")} ${simTag}</span></div>
                    `;
                } else {
                    // Generic attributes renderer
                    for (const [k, v] of Object.entries(pVal)) {
                        if (k === "available" || k === "simulated") continue;
                        contentHtml += `<div class="plugin-metric"><span>${k}:</span><span>${v}</span></div>`;
                    }
                }
            } else {
                contentHtml += `<div style="font-size:0.8rem; color:var(--text-secondary); text-align:center; margin-top:0.5rem;">Not available</div>`;
            }
            card.innerHTML = contentHtml;
            pluginsContainer.appendChild(card);
        }
    }

    // 8. Live Anomalies Feed
    const anomalyContainer = document.getElementById("anomaly-feed-container");
    anomalyContainer.innerHTML = "";
    const anomalies = data.anomalies || [];
    
    if (anomalies.length === 0) {
        anomalyContainer.innerHTML = `
            <div style="text-align: center; color: var(--color-healthy); margin-top: 2.5rem; font-weight:500;">
                ✓ System behavioral baselines normal.
            </div>
        `;
    } else {
        anomalies.forEach(anom => {
            const timeStr = new Date(anom.timestamp * 1000).toLocaleTimeString();
            const item = document.createElement("div");
            item.className = `anomaly-item ${anom.severity}`;
            item.innerHTML = `
                <div class="anomaly-meta">
                    <span class="badge" style="background: rgba(255,255,255,0.08); color:#fff; font-weight:600;">${anom.metric}</span>
                    <span>${timeStr}</span>
                </div>
                <div class="anomaly-desc">${anom.description}</div>
                <div class="anomaly-meta" style="margin-top:0.25rem;">
                    <span>Severity: <strong style="color:var(--text-primary);">${anom.severity}</strong></span>
                    <span>Z-Score: ${anom.deviation_z}</span>
                </div>
            `;
            anomalyContainer.appendChild(item);
        });
    }
}

// Load Troubleshooting diagnoses from separate endpoint for confirmation
async function updateTroubleshooting() {
    try {
        const res = await fetch("/api/health");
        if (res.ok) {
            const data = await res.json();
            const container = document.getElementById("troubleshoot-container");
            container.innerHTML = "";
            const diagnoses = data.diagnoses || [];

            if (diagnoses.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; color: var(--color-healthy); margin-top: 2.5rem; font-weight:500;">
                        ✓ No hardware recommendations.
                    </div>
                `;
            } else {
                diagnoses.forEach(diag => {
                    const item = document.createElement("div");
                    item.className = "diagnosis-item";
                    
                    let statusColor;
                    if (diag.severity === "HIGH") statusColor = "var(--color-critical)";
                    else if (diag.severity === "MEDIUM") statusColor = "var(--color-degraded)";
                    else statusColor = "var(--color-healthy)";

                    let recsHtml = "";
                    diag.recommendations.forEach(rec => {
                        recsHtml += `<li>${rec}</li>`;
                    });

                    item.innerHTML = `
                        <div class="diag-title" style="color:${statusColor};">
                            <span>${diag.type}</span>
                            <span class="badge" style="background:rgba(255,255,255,0.05); color:${statusColor};">${diag.severity}</span>
                        </div>
                        <div style="font-size:0.85rem; font-weight:500;">${diag.message}</div>
                        <ul class="diag-rec">
                            ${recsHtml}
                        </ul>
                    `;
                    container.appendChild(item);
                });
            }
        }
    } catch (e) {
        console.error("Troubleshooting update failed", e);
    }
}

// WebSocket connection lifecycle
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;
    const connDot = document.getElementById("connection-dot");
    const connText = document.getElementById("connection-text");
    
    console.log(`Connecting WebSocket to: ${wsUrl}`);
    const socket = new WebSocket(wsUrl);

    socket.onopen = function() {
        console.log("WebSocket connected.");
        connDot.style.backgroundColor = "var(--color-healthy)";
        connDot.style.boxShadow = "0 0 10px var(--color-healthy)";
        connDot.classList.add("blinking");
        connText.textContent = "Live Stream Connected";
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        updateDashboard(data);
        updateTroubleshooting();
    };

    socket.onclose = function() {
        console.warn("WebSocket disconnected. Falling back to HTTP polling.");
        connDot.style.backgroundColor = "var(--color-degraded)";
        connDot.style.boxShadow = "0 0 10px var(--color-degraded)";
        connText.textContent = "Reconnecting...";
        
        // Retry connection in 3 seconds
        setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = function(err) {
        console.error("WebSocket error:", err);
        socket.close();
    };
}

// Main initialization
window.addEventListener("DOMContentLoaded", () => {
    // Initialise Chart.js contexts
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    const memCtx = document.getElementById('memChart').getContext('2d');

    cpuChart = createTelemetryChart(cpuCtx, 'CPU', '#3b82f6', 'rgba(59, 130, 246, 0.1)');
    memChart = createTelemetryChart(memCtx, 'Memory', '#8b5cf6', 'rgba(139, 92, 246, 0.1)');

    // Start WebSocket Stream
    connectWebSocket();
});
