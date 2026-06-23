// Global configurations
const MAX_CHART_POINTS = 15;
let cpuChart, memChart;
let cpuHistory = [];
let memHistory = [];
let chartLabels = [];

// Task Manager state variables
let lastProcesses = [];
let killConfirmPids = {};
let killConfirmTimeouts = {};

// Initialize History Data
for (let i = 0; i < MAX_CHART_POINTS; i++) {
    cpuHistory.push(0);
    memHistory.push(0);
    chartLabels.push("");
}

// Chart.js helper to create premium line charts
function createTelemetryChart(ctx, label, colorGradStart, colorGradStop) {
    if (typeof Chart === 'undefined') {
        console.warn("Chart.js is not defined. Telemetry graphs will be disabled.");
        return null;
    }
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
    if (cpuChart) cpuChart.update();

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
    if (memChart) memChart.update();

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
    const freezeCheckbox = document.getElementById("freeze-telemetry");
    const isFrozen = freezeCheckbox ? freezeCheckbox.checked : false;
    
    if (!isFrozen) {
        lastProcesses = data.processes || [];
    }
    renderProcessesTable();

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
                } else if (pName === "network_telemetry") {
                    contentHtml += `
                        <div class="plugin-metric"><span>Bytes Recv Sec:</span><span style="font-weight:600; color:#10b981;">${formatBytes(pVal.bytes_recv_sec)}/s</span></div>
                        <div class="plugin-metric"><span>Bytes Sent Sec:</span><span style="font-weight:600; color:#60a5fa;">${formatBytes(pVal.bytes_sent_sec)}/s</span></div>
                        <div class="plugin-metric"><span>Active Connections:</span><span>${pVal.active_connections}</span></div>
                        <div class="plugin-metric"><span>Network Status:</span><span style="font-weight:600; color:${pVal.network_status === 'ONLINE' ? '#10b981' : '#ef4444'};">${pVal.network_status}</span></div>
                    `;
                } else if (pName === "disk_health") {
                    contentHtml += `
                        <div class="plugin-metric"><span>SMART Status:</span><span style="font-weight:600; color:${pVal.smart_status === 'PASSED' ? '#10b981' : '#f59e0b'};">${pVal.smart_status}</span></div>
                        <div class="plugin-metric"><span>Disk Temp:</span><span>${pVal.disk_temp_c}°C</span></div>
                        <div class="plugin-metric"><span>Wear Level:</span><span>${pVal.wear_level_percent}%</span></div>
                        <div class="plugin-metric"><span>Read Latency:</span><span>${pVal.read_latency_ms} ms</span></div>
                        <div class="plugin-metric"><span>Write Latency:</span><span>${pVal.write_latency_ms} ms</span></div>
                    `;
                } else {
                    // Generic attributes renderer
                    for (const [k, v] of Object.entries(pVal)) {
                        if (k === "available" || k === "simulated") continue;
                        const displayKey = k.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                        contentHtml += `<div class="plugin-metric"><span>${displayKey}:</span><span>${v}</span></div>`;
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
        const cpuPct = data.cpu ? data.cpu.usage_percent.toFixed(1) : "0.0";
        const memPct = data.memory ? data.memory.usage_percent.toFixed(1) : "0.0";
        const net_data = data.plugins_data ? data.plugins_data.network_telemetry : null;
        const activeConns = net_data && net_data.active_connections ? net_data.active_connections : "0";

        anomalyContainer.innerHTML = `
            <div style="text-align: center; color: var(--color-healthy); margin-bottom: 1.5rem; font-weight: 500; margin-top: 1rem;">
                ✓ Behavioral baselines normal.
            </div>
            <div style="background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.04); border-radius: 16px; padding: 1.25rem; backdrop-filter: blur(8px);">
                <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-secondary); margin-bottom:0.75rem; letter-spacing:1px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:0.35rem; font-weight:600;">Telemetry Watchdog Audit</div>
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.6rem; color:var(--text-primary);">
                    <span>CPU Threshold Watcher</span>
                    <span style="color:var(--color-healthy); font-weight:600;">[OK] (${cpuPct}%)</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.6rem; color:var(--text-primary);">
                    <span>RAM Saturation Watcher</span>
                    <span style="color:var(--color-healthy); font-weight:600;">[OK] (${memPct}%)</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.6rem; color:var(--text-primary);">
                    <span>Socket Leak Detector</span>
                    <span style="color:var(--color-healthy); font-weight:600;">[OK] (${activeConns})</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--text-primary);">
                    <span>Disk I/O Write Latency</span>
                    <span style="color:var(--color-healthy); font-weight:600;">[OK]</span>
                </div>
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
                    <div style="text-align: center; color: var(--color-healthy); margin-bottom: 1.5rem; font-weight:500; margin-top: 1rem;">
                        ✓ No hardware recommendations.
                    </div>
                    <div style="background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.04); border-radius: 16px; padding: 1.25rem; backdrop-filter: blur(8px);">
                        <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-secondary); margin-bottom:0.75rem; letter-spacing:1px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:0.35rem; font-weight:600;">Hardware Diagnostics Checklist</div>
                        <div style="display:flex; align-items:center; gap:0.5rem; font-size:0.8rem; margin-bottom:0.6rem; color:var(--text-primary);">
                            <span style="color:var(--color-healthy); font-weight:bold;">✓</span>
                            <span>CPU Thermal Throttling Audit: <strong style="color:var(--color-healthy);">PASSED</strong></span>
                        </div>
                        <div style="display:flex; align-items:center; gap:0.5rem; font-size:0.8rem; margin-bottom:0.6rem; color:var(--text-primary);">
                            <span style="color:var(--color-healthy); font-weight:bold;">✓</span>
                            <span>RAM Physical Allocation Audit: <strong style="color:var(--color-healthy);">PASSED</strong></span>
                        </div>
                        <div style="display:flex; align-items:center; gap:0.5rem; font-size:0.8rem; margin-bottom:0.6rem; color:var(--text-primary);">
                            <span style="color:var(--color-healthy); font-weight:bold;">✓</span>
                            <span>HDD/SSD SMART Wear Level Audit: <strong style="color:var(--color-healthy);">PASSED</strong></span>
                        </div>
                        <div style="display:flex; align-items:center; gap:0.5rem; font-size:0.8rem; color:var(--text-primary);">
                            <span style="color:var(--color-healthy); font-weight:bold;">✓</span>
                            <span>Indexer & SysMain System Check: <strong style="color:var(--color-healthy);">PASSED</strong></span>
                        </div>
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
        updateSuggestions();
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

// Fetch Optimization Suggestions from endpoint
// Premium Toast display helper
function showToast(title, message, isError = false) {
    const toast = document.getElementById("syslens-toast");
    const tTitle = document.getElementById("toast-title");
    const tBody = document.getElementById("toast-body");
    if (!toast || !tTitle || !tBody) return;

    tTitle.innerHTML = title;
    tTitle.style.color = isError ? "var(--color-critical)" : "var(--color-healthy)";
    tBody.innerHTML = message;

    toast.classList.add("show");

    if (window.toastTimeout) {
        clearTimeout(window.toastTimeout);
    }
    window.toastTimeout = setTimeout(() => {
        toast.classList.remove("show");
    }, 6000);
}

// Fetch Optimization Suggestions from endpoint
async function updateSuggestions() {
    const container = document.getElementById("suggestions-container");
    if (!container) return;
    try {
        const res = await fetch("/api/suggestions");
        if (res.ok) {
            const data = await res.json();
            const sugs = data.suggestions || [];
            
            if (sugs.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; color: var(--color-healthy); margin-top: 2.5rem; font-weight: 500;">
                        ✓ System fully optimized!
                    </div>
                `;
                return;
            }
            
            let html = "";
            let hasSafe = false;
            sugs.forEach(s => {
                s.actions.forEach(a => { if (a.risk === "SAFE") hasSafe = true; });
            });
            
            if (hasSafe) {
                html += `
                    <button id="web-optimize-btn" onclick="runWebOptimization()" style="width: 100%; padding: 0.6rem; background: var(--gradient-healthy); border: none; border-radius: 8px; color: #fff; font-weight: 600; cursor: pointer; margin-bottom: 1rem; box-shadow: 0 4px 12px var(--color-healthy-glow); transition: transform 0.2s;">
                        ⚡ Run Optimization
                    </button>
                `;
            }
            
            sugs.forEach(sug => {
                html += `
                    <div style="margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <div style="font-weight: 600; color: #f59e0b; font-size: 0.9rem; margin-bottom: 0.25rem;">
                            ${sug.category}: ${sug.issue}
                        </div>
                        <ul style="padding-left: 1.25rem; font-size: 0.8rem; color: var(--text-secondary); list-style-type: none;">
                `;
                sug.actions.forEach(act => {
                    let riskColor = "#10b981";
                    if (act.risk === "MEDIUM") riskColor = "#f59e0b";
                    if (act.risk === "HIGH RISK") riskColor = "#ef4444";
                    html += `<li style="margin-bottom: 0.25rem; display: flex; justify-content: space-between;">
                        <span>• ${act.name}</span>
                        <span style="font-size:0.7rem; color:${riskColor}; font-weight:600; margin-left:4px;">[${act.risk}]</span>
                    </li>`;
                });
                html += `
                        </ul>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
    } catch (err) {
        console.error("Error fetching suggestions:", err);
    }
}

async function runWebOptimization() {
    const btn = document.getElementById("web-optimize-btn");
    if (!btn) return;
    btn.disabled = true;
    btn.textContent = "Optimizing...";
    btn.style.background = "#4b5563";

    const profileSelect = document.getElementById("optimize-profile-select");
    const profile = profileSelect ? profileSelect.value : "safe";

    try {
        const res = await fetch(`/api/optimize?profile=${profile}`, { method: "POST" });
        if (res.ok) {
            const results = await res.json();
            
            let tempFilesRemoved = 0;
            let rbNote = "Skipped";
            let fixesList = [];
            
            if (results.results) {
                const cleanup = results.results[0] || [];
                const fixes = results.results[1] || [];
                
                cleanup.forEach(r => {
                    if (r.task === "TEMP_CLEAN") {
                        tempFilesRemoved = r.files_removed || 0;
                    } else if (r.task === "RECYCLE_BIN") {
                        rbNote = r.note || r.status || "Completed";
                    }
                });
                
                fixes.forEach(f => {
                    fixesList.push(f.fix);
                });
            }
            
            let msg = `• Profile applied: <strong>${profile.toUpperCase()}</strong><br>` +
                      `• Temp files cleared: <strong>${tempFilesRemoved}</strong> files<br>` +
                      `• Recycle Bin: <strong>${rbNote}</strong>`;
                      
            if (fixesList.length > 0) {
                msg += `<br>• Resource remedies: <strong>${fixesList.join(", ")}</strong>`;
            }
            
            showToast("⚡ Optimization Complete", msg, false);
            updateSuggestions();
        } else {
            showToast("✗ Optimization Failed", "Backend encountered an error during optimization.", true);
        }
    } catch (err) {
        showToast("✗ Optimization Error", err.message || err, true);
    } finally {
        btn.disabled = false;
        btn.textContent = "⚡ Run Optimization";
        btn.style.background = "var(--gradient-healthy)";
    }
}

async function runWebRollback() {
    const btn = document.getElementById("web-rollback-btn");
    if (!btn) return;
    btn.disabled = true;
    const oldText = btn.textContent;
    btn.textContent = "Reverting...";
    
    try {
        const res = await fetch("/api/rollback", { method: "POST" });
        if (res.ok) {
            const results = await res.json();
            if (results.status === "no_actions_to_rollback") {
                showToast("⚠ Rollback Skipped", "No previous actions in history to rollback.", true);
            } else {
                const reverted = results.details || [];
                let msg = reverted.length > 0 ? reverted.map(c => `• ${c}`).join("<br> ") : "Last transaction reverted.";
                showToast("↩ Rollback Executed", msg, false);
                updateSuggestions();
            }
        } else {
            showToast("✗ Rollback Failed", "Failed to contact rollback backend.", true);
        }
    } catch (err) {
        showToast("✗ Rollback Error", err.message || err, true);
    } finally {
        btn.disabled = false;
        btn.textContent = oldText;
    }
}

// Helper functions for Task Manager
function renderProcessesTable() {
    const procTableBody = document.getElementById("process-table-body");
    if (!procTableBody) return;

    const searchInput = document.getElementById("process-search");
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    
    // Filter processes
    const filtered = lastProcesses.filter(proc => {
        if (!query) return true;
        return proc.name.toLowerCase().includes(query) || proc.pid.toString().includes(query);
    });

    if (filtered.length === 0) {
        procTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">No matching processes.</td></tr>`;
        return;
    }

    procTableBody.innerHTML = "";
    filtered.forEach(proc => {
        const tr = document.createElement("tr");
        
        let btnText = "Kill";
        let btnClass = "btn-kill";
        if (killConfirmPids[proc.pid]) {
            btnText = "Confirm?";
            btnClass = "btn-kill confirm";
        }

        tr.innerHTML = `
            <td style="color:#60a5fa; font-weight:600;">${proc.pid}</td>
            <td style="font-weight:500;">${proc.name}</td>
            <td><span class="badge badge-cpu">${proc.cpu_percent}%</span></td>
            <td><span class="badge badge-mem">${proc.memory_percent}%</span></td>
            <td>${proc.status}</td>
            <td style="color:var(--text-secondary);">${proc.username}</td>
            <td style="text-align: right;">
                <button id="kill-btn-${proc.pid}" class="${btnClass}" onclick="handleKillClick(event, ${proc.pid}, '${proc.name}')">${btnText}</button>
            </td>
        `;
        procTableBody.appendChild(tr);
    });
}

async function handleKillClick(event, pid, name) {
    event.stopPropagation();
    const btn = document.getElementById(`kill-btn-${pid}`);
    if (!btn) return;

    if (!killConfirmPids[pid]) {
        // First click: activate confirmation
        killConfirmPids[pid] = true;
        btn.textContent = "Confirm?";
        btn.className = "btn-kill confirm";

        // Set a timeout to clear the confirmation state after 3 seconds
        killConfirmTimeouts[pid] = setTimeout(() => {
            delete killConfirmPids[pid];
            delete killConfirmTimeouts[pid];
            renderProcessesTable();
        }, 3000);
    } else {
        // Second click: execute termination
        if (killConfirmTimeouts[pid]) {
            clearTimeout(killConfirmTimeouts[pid]);
            delete killConfirmTimeouts[pid];
        }
        delete killConfirmPids[pid];

        btn.disabled = true;
        btn.textContent = "Killing...";
        btn.style.background = "#4b5563";
        btn.style.borderColor = "#6b7280";
        btn.style.color = "#9ca3af";

        try {
            const res = await fetch(`/api/processes/kill?pid=${pid}`, { method: "POST" });
            if (res.ok) {
                const result = await res.json();
                showToast("⚡ Process Terminated", `Successfully terminated <strong>${name}</strong> (PID ${pid}).`, false);
                
                // Immediately remove the process from our local cache so it disappears instantly
                lastProcesses = lastProcesses.filter(p => p.pid !== pid);
                renderProcessesTable();
            } else {
                const errData = await res.json();
                const detail = errData.detail || "Access denied or backend error.";
                showToast("✗ Termination Failed", `Failed to kill <strong>${name}</strong> (PID ${pid}): ${detail}`, true);
                renderProcessesTable();
            }
        } catch (err) {
            showToast("✗ Termination Error", err.message || err, true);
            renderProcessesTable();
        }
    }
}

window.runWebOptimization = runWebOptimization;
window.runWebRollback = runWebRollback;
window.handleKillClick = handleKillClick;

// Playbook State Variables
let playbookCommands = [];
let activePlaybookCommand = null;
let playbookAbortController = null;

async function fetchPlaybookCommands() {
    try {
        const res = await fetch("/api/playbook/commands");
        if (res.ok) {
            const data = await res.json();
            playbookCommands = data.commands || [];
            renderPlaybookCommands();
        }
    } catch (e) {
        console.error("Failed to load playbook commands:", e);
    }
}

function renderPlaybookCommands() {
    const repairList = document.getElementById("playbook-repair-list");
    const powerList = document.getElementById("playbook-power-list");
    const networkList = document.getElementById("playbook-network-list");

    if (!repairList || !powerList || !networkList) return;

    repairList.innerHTML = "";
    powerList.innerHTML = "";
    networkList.innerHTML = "";

    playbookCommands.forEach(cmd => {
        const btn = document.createElement("button");
        btn.className = "playbook-btn";
        
        let typeBadge = cmd.type === "gui" ? "💻 GUI" : "⌨️ CLI";
        btn.innerHTML = `
            <span style="font-weight:600;">${cmd.name}</span>
            <span style="font-size:0.7rem; opacity:0.6; background:rgba(255,255,255,0.06); padding:0.1rem 0.3rem; border-radius:4px;">${typeBadge}</span>
        `;
        btn.onclick = () => openPlaybookModal(cmd);

        if (cmd.category === "repair") {
            repairList.appendChild(btn);
        } else if (cmd.category === "power") {
            powerList.appendChild(btn);
        } else if (cmd.category === "network") {
            networkList.appendChild(btn);
        }
    });
}

function openPlaybookModal(cmd) {
    activePlaybookCommand = cmd;
    
    document.getElementById("modal-title").textContent = `Execute ${cmd.name}`;
    document.getElementById("modal-caution").textContent = cmd.caution;
    document.getElementById("modal-cmd-string").textContent = cmd.cmd_string;
    
    // Reset Terminal
    const terminalEl = document.getElementById("modal-terminal");
    const terminalWrapper = document.getElementById("modal-terminal-wrapper");
    if (terminalEl) terminalEl.textContent = "";
    if (terminalWrapper) terminalWrapper.style.display = "none";
    
    // Reset Action Buttons
    const runBtn = document.getElementById("modal-btn-run");
    if (runBtn) {
        runBtn.disabled = false;
        runBtn.textContent = "Execute Command";
        runBtn.style.background = "var(--gradient-primary)";
    }
    
    // Show Modal
    document.getElementById("playbook-modal").classList.add("show");
}

function closePlaybookModal() {
    // If running, abort fetch stream
    if (playbookAbortController) {
        playbookAbortController.abort();
        playbookAbortController = null;
    }
    document.getElementById("playbook-modal").classList.remove("show");
    activePlaybookCommand = null;
}

async function executePlaybookCommand() {
    if (!activePlaybookCommand) return;
    const cmd = activePlaybookCommand;
    const runBtn = document.getElementById("modal-btn-run");
    const terminalWrapper = document.getElementById("modal-terminal-wrapper");
    const terminalEl = document.getElementById("modal-terminal");

    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = "Executing...";
        runBtn.style.background = "#4b5563";
    }

    if (terminalWrapper) terminalWrapper.style.display = "block";
    if (terminalEl) terminalEl.textContent = `[SysLens Observability Orchestrator]\n[Launching task: ${cmd.cmd_string}]\n\n`;

    if (cmd.type === "gui") {
        try {
            const res = await fetch(`/api/playbook/run/${cmd.id}`, { method: "POST" });
            if (res.ok) {
                const data = await res.json();
                if (terminalEl) terminalEl.textContent += `\n[Status]: ${data.message}\n[Finished successfully]\n`;
                showToast("⚡ Command Executed", data.message, false);
                setTimeout(() => {
                    closePlaybookModal();
                }, 2000);
            } else {
                const data = await res.json();
                if (terminalEl) terminalEl.textContent += `\n[Error]: ${data.detail || "Failed to launch GUI tool."}\n`;
                showToast("✗ Execution Failed", data.detail || "Failed to launch GUI tool.", true);
                if (runBtn) {
                    runBtn.disabled = false;
                    runBtn.textContent = "Retry Execution";
                    runBtn.style.background = "var(--gradient-primary)";
                }
            }
        } catch (e) {
            if (terminalEl) terminalEl.textContent += `\n[Connection Error]: ${e.message}\n`;
            showToast("✗ Connection Error", e.message, true);
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.textContent = "Retry Execution";
                runBtn.style.background = "var(--gradient-primary)";
            }
        }
    } else {
        // CLI Stream execution
        playbookAbortController = new AbortController();
        try {
            const response = await fetch(`/api/playbook/run/${cmd.id}`, {
                method: "POST",
                signal: playbookAbortController.signal
            });

            if (!response.ok) {
                const errText = await response.text();
                if (terminalEl) terminalEl.textContent += `\n[Error]: HTTP ${response.status} - ${errText}\n`;
                if (runBtn) {
                    runBtn.disabled = false;
                    runBtn.textContent = "Retry Execution";
                    runBtn.style.background = "var(--gradient-primary)";
                }
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                if (terminalEl) {
                    terminalEl.textContent += chunk;
                    terminalEl.scrollTop = terminalEl.scrollHeight;
                }
            }
            showToast("⚡ Command Completed", `Playbook command <strong>${cmd.name}</strong> completed.`, false);
        } catch (err) {
            if (err.name === "AbortError") {
                if (terminalEl) terminalEl.textContent += `\n[Process aborted by user]\n`;
            } else {
                if (terminalEl) terminalEl.textContent += `\n[Execution Error]: ${err.message}\n`;
                if (runBtn) {
                    runBtn.disabled = false;
                    runBtn.textContent = "Retry Execution";
                    runBtn.style.background = "var(--gradient-primary)";
                }
            }
        } finally {
            playbookAbortController = null;
            if (runBtn && runBtn.textContent === "Executing...") {
                runBtn.disabled = false;
                runBtn.textContent = "Execute Command";
                runBtn.style.background = "var(--gradient-primary)";
            }
        }
    }
}

// Expose playbook functions to global window scope
window.openPlaybookModal = openPlaybookModal;
window.closePlaybookModal = closePlaybookModal;
window.executePlaybookCommand = executePlaybookCommand;

// Main initialization
window.addEventListener("DOMContentLoaded", () => {
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    const memCtx = document.getElementById('memChart').getContext('2d');

    cpuChart = createTelemetryChart(cpuCtx, 'CPU', '#3b82f6', 'rgba(59, 130, 246, 0.1)');
    memChart = createTelemetryChart(memCtx, 'Memory', '#8b5cf6', 'rgba(139, 92, 246, 0.1)');

    // Start WebSocket Stream & load suggestions
    connectWebSocket();
    updateSuggestions();

    // Fetch and render playbook commands
    fetchPlaybookCommands();

    // Hook search inputs
    const searchInput = document.getElementById("process-search");
    if (searchInput) {
        searchInput.addEventListener("input", renderProcessesTable);
    }
});
