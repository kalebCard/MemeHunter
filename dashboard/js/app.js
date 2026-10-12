/**
 * MemeHunter Autonomous Alpha Cockpit - Frontend Logic
 * Conexión reactiva con API REST y renderizado interactivo con Chart.js.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Estado local reactivo
  let appState = {
    strategies: [
      { id: "ALPHA_MOM_01", formula: "ts_rank(close, 14)", status: "LIVE", weight: 0.65, backtest_sharpe: 2.10, ic: 0.082, pval: 0.001 },
      { id: "ALPHA_VOL_02", formula: "ts_zscore((high - low), 10) * rvol", status: "LIVE", weight: 0.35, backtest_sharpe: 1.85, ic: 0.065, pval: 0.004 },
      { id: "ALPHA_DECAYED_03", formula: "ts_delay(close, 10)", status: "ALPHA_DECAY", weight: 0.00, backtest_sharpe: 1.40, ic: -0.012, pval: 0.320 },
      { id: "SANDBOX_LLM_04", formula: "ts_rank(rvol, 10) * (close - vwap)", status: "SANDBOX", weight: 0.00, backtest_sharpe: 1.95, ic: 0.074, pval: 0.002 }
    ],
    autopsies: [
      {
        factor_id: "ALPHA_DECAYED_03",
        diagnosis: "ALPHA_DECAY_VOLATILITY_COMPRESSION",
        root_cause: "El factor perdió correlación predictiva debido a una compresión de volatilidad y saturación de microestructura.",
        recommendation: "Excluir factores basados en momentum de cierre simple y priorizar desbalances de volumen acumulado (volume imbalance / rvol).",
        confidence: 0.88,
        actions: ["ISOLATE_FACTOR", "REDUCE_WEIGHT_TO_ZERO", "MINE_VOLUME_MICROSTRUCTURE"]
      }
    ],
    niches: [
      { niche: "MOMENTUM_PRICE_LOW_DEPTH", formula: "ts_rank(close, 10)", ic_ir: 2.15, status: "LIDER" },
      { niche: "MICROSTRUCTURE_VOLUME_LOW_DEPTH", formula: "ts_rank(volume, 14)", ic_ir: 2.42, status: "LIDER" },
      { niche: "VOLATILITY_HIGH_DEPTH", formula: "ts_zscore((high - low), 10) * rvol", ic_ir: 1.98, status: "LIDER" },
      { niche: "MICROSTRUCTURE_VOLUME_HIGH_DEPTH", formula: "ts_rank(rvol, 10) * (close - vwap)", ic_ir: 2.65, status: "LIDER" }
    ],
    logs: [
      { ts: "22:40:12", type: "info", text: "Alpha Miner Daemon activo en background (Proceso 24/7)." },
      { ts: "22:42:05", type: "warn", text: "Alerta CUSUM: ALPHA_DECAYED_03 entra en degradación de señal (IC: -0.012)." },
      { ts: "22:42:07", type: "ai", text: "Autopsia OpenRouter (DeepSeek-R1): ALPHA_DECAY_VOLATILITY_COMPRESSION confirmado." },
      { ts: "22:42:08", type: "ai", text: "OpenRouter sintetiza 5 nuevos factores ortogonales basados en microestructura." },
      { ts: "22:42:09", type: "info", text: "Rebalanceo HRP ejecutado: 100% capital reasignado a ALPHA_MOM_01 y ALPHA_VOL_02." }
    ]
  };

  let equityChart = null;
  let icChart = null;

  // 1. Inicialización de Gráficos Chart.js
  function initCharts() {
    const ctxEquity = document.getElementById('equityChart').getContext('2d');
    const gradientEquity = ctxEquity.createLinearGradient(0, 0, 0, 260);
    gradientEquity.addColorStop(0, 'rgba(0, 242, 254, 0.4)');
    gradientEquity.addColorStop(1, 'rgba(0, 242, 254, 0.0)');

    const labels = Array.from({ length: 30 }, (_, i) => `Día ${i + 1}`);
    const equityData = [1000];
    for (let i = 1; i < 30; i++) {
      const growth = (Math.random() * 0.025 - 0.005);
      equityData.push(Math.round(equityData[i - 1] * (1 + growth) * 100) / 100);
    }

    equityChart = new Chart(ctxEquity, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Valor Cartera USDT (HRP Auto-Rebalance)',
          data: equityData,
          borderColor: '#00f2fe',
          backgroundColor: gradientEquity,
          borderWidth: 2.5,
          tension: 0.3,
          fill: true,
          pointRadius: 0,
          pointHoverRadius: 5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } } },
          y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } } }
        }
      }
    });

    // Gráfico de IC
    const ctxIC = document.getElementById('icChart').getContext('2d');
    icChart = new Chart(ctxIC, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'ALPHA_MOM_01 (Sano)',
            data: labels.map(() => 0.06 + Math.random() * 0.04),
            borderColor: '#10b981',
            borderWidth: 2,
            tension: 0.2,
            pointRadius: 0
          },
          {
            label: 'ALPHA_DECAYED_03 (Decaimiento)',
            data: labels.map((_, idx) => idx > 15 ? 0.02 - (idx - 15) * 0.005 : 0.06 + Math.random() * 0.02),
            borderColor: '#f43f5e',
            borderWidth: 2,
            tension: 0.2,
            pointRadius: 0
          },
          {
            label: 'Umbral Mínimo IC (0.03)',
            data: Array(30).fill(0.03),
            borderColor: 'rgba(245, 158, 11, 0.6)',
            borderWidth: 1.5,
            borderDash: [5, 5],
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
          }
        },
        scales: {
          x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } } },
          y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } } }
        }
      }
    });
  }

  // 2. Renderizado de la Tabla de la Incubadora
  function renderIncubatorTable() {
    const tbody = document.getElementById('incubatorTableBody');
    tbody.innerHTML = '';

    appState.strategies.forEach(strat => {
      const tr = document.createElement('tr');

      let badgeClass = 'status-live';
      if (strat.status === 'SANDBOX') badgeClass = 'status-sandbox';
      if (strat.status === 'ALPHA_DECAY') badgeClass = 'status-decay';
      if (strat.status === 'RETIRED') badgeClass = 'status-retired';

      const weightPct = (strat.weight * 100).toFixed(1) + '%';
      const icColor = strat.ic >= 0.03 ? 'color: var(--accent-emerald)' : 'color: var(--accent-rose)';

      tr.innerHTML = `
        <td style="font-weight: 700; color: #fff;">${strat.id}</td>
        <td style="color: var(--text-secondary); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${strat.formula}">
          ${strat.formula}
        </td>
        <td><span class="status-pill ${badgeClass}">${strat.status}</span></td>
        <td style="font-weight: 700; color: var(--accent-cyan);">${weightPct}</td>
        <td>${strat.backtest_sharpe.toFixed(2)}</td>
        <td style="${icColor}; font-weight: 600;">${strat.ic >= 0 ? '+' : ''}${strat.ic.toFixed(3)}</td>
        <td>
          <button class="btn-action" style="padding: 4px 10px; font-size: 0.7rem;" onclick="window.auditStrategy('${strat.id}')">
            Auditar
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // 3. Renderizado de Autopsias IA
  function renderAutopsies() {
    const container = document.getElementById('autopsyListContainer');
    container.innerHTML = '';

    if (appState.autopsies.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">No hay factores en decaimiento actualmente.</p>';
      return;
    }

    appState.autopsies.forEach(aut => {
      const card = document.createElement('div');
      card.className = 'autopsy-card';
      card.innerHTML = `
        <div class="autopsy-header">
          <span class="autopsy-title">FACTOR: ${aut.factor_id}</span>
          <span class="autopsy-diag">${aut.diagnosis}</span>
        </div>
        <div class="autopsy-body">
          <strong>Causa Raíz:</strong> ${aut.root_cause}
        </div>
        <div class="autopsy-rec">
          <strong>Recomendación IA:</strong> ${aut.recommendation}
        </div>
      `;
      container.appendChild(card);
    });
  }

  // 4. Renderizado de Nichos de Diversidad (MAP-Elites)
  function renderNiches() {
    const container = document.getElementById('diversityNichesContainer');
    container.innerHTML = '';

    appState.niches.forEach(n => {
      const div = document.createElement('div');
      div.style.cssText = 'padding: 10px 14px; background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,255,255,0.05);';
      div.innerHTML = `
        <div>
          <div style="font-size: 0.72rem; color: var(--accent-cyan); font-family: var(--font-mono);">${n.niche}</div>
          <div style="font-size: 0.8rem; color: var(--text-secondary); font-family: var(--font-mono);">${n.formula}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 0.85rem; font-weight: 700; color: var(--accent-purple); font-family: var(--font-mono);">IC_IR ${n.ic_ir.toFixed(2)}</div>
          <span class="status-pill status-live" style="font-size: 0.65rem;">${n.status}</span>
        </div>
      `;
      container.appendChild(div);
    });
  }

  // 5. Renderizado del Terminal Log
  function renderLogs() {
    const consoleEl = document.getElementById('terminalLogConsole');
    consoleEl.innerHTML = '';

    appState.logs.forEach(log => {
      const line = document.createElement('div');
      line.className = 'log-line';
      let typeClass = '';
      if (log.type === 'warn') typeClass = 'log-warn';
      if (log.type === 'error') typeClass = 'log-error';
      if (log.type === 'ai') typeClass = 'log-ai';

      line.innerHTML = `<span class="log-ts">[${log.ts}]</span> <span class="${typeClass}">${log.text}</span>`;
      consoleEl.appendChild(line);
    });
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function addLog(type, text) {
    const now = new Date();
    const ts = now.toTimeString().split(' ')[0];
    appState.logs.push({ ts, type, text });
    renderLogs();
  }

  // 6. Conexión con el Backend REST API
  async function fetchBackendStatus() {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        if (data.strategies) appState.strategies = data.strategies;
        if (data.autopsies) appState.autopsies = data.autopsies;
        if (data.niches) appState.niches = data.niches;
        updateUI();
      }
    } catch (e) {
      // Si corre como página estática sin server.py activo, utiliza el mock interactivo local
      console.log('Modo visual local independiente activo.');
    }
  }

  // 7. Acciones de los Botones
  document.getElementById('btn-trigger-cycle').addEventListener('click', async () => {
    addLog('info', 'Ejecutando ciclo de auto-diagnóstico y auto-sanación...');
    try {
      const res = await fetch('/api/trigger-loop', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        addLog('ai', `Ciclo completado. Acciones ejecutadas: ${data.actions ? data.actions.length : 1}`);
        fetchBackendStatus();
        return;
      }
    } catch (e) {}

    // Simulación interactiva local
    setTimeout(() => {
      addLog('warn', 'Auditoría CUSUM: ALPHA_DECAYED_03 ratificado en ALPHA_DECAY.');
      addLog('ai', 'Promoviendo factor SANDBOX_LLM_04 a producción y rebalanceando capital...');
      appState.strategies.forEach(s => {
        if (s.id === 'SANDBOX_LLM_04') {
          s.status = 'LIVE';
          s.weight = 0.25;
        }
        if (s.id === 'ALPHA_MOM_01') s.weight = 0.50;
        if (s.id === 'ALPHA_VOL_02') s.weight = 0.25;
      });
      updateUI();
      addLog('info', 'Nuevo vector de pesos HRP aplicado con éxito.');
    }, 600);
  });

  document.getElementById('btn-synthesize-ai').addEventListener('click', async () => {
    addLog('ai', 'Conectando con OpenRouter (DeepSeek-V3 / Qwen-2.5-Coder)...');
    try {
      const res = await fetch('/api/synthesize-alpha', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        addLog('ai', `OpenRouter sintetizó ${data.count || 3} nuevos alphas validados con AST.`);
        fetchBackendStatus();
        return;
      }
    } catch (e) {}

    // Simulación interactiva local
    setTimeout(() => {
      const newFactorId = `LLM_NEW_${Math.floor(Math.random() * 900 + 100)}`;
      appState.strategies.push({
        id: newFactorId,
        formula: "ts_rank(volume_delta, 10) * div(high - low, close)",
        status: "SANDBOX",
        weight: 0.0,
        backtest_sharpe: 2.25,
        ic: 0.088,
        pval: 0.0005
      });
      addLog('ai', `Nueva fórmula validada con AST e inyectada a SANDBOX: ${newFactorId}`);
      updateUI();
    }, 800);
  });

  window.auditStrategy = function(id) {
    addLog('info', `Iniciando auditoría forense para ${id}...`);
    const strat = appState.strategies.find(s => s.id === id);
    if (strat) {
      alert(`Auditoría Cuantitativa de ${strat.id}:\nFórmula: ${strat.formula}\nEstado: ${strat.status}\nSharpe OOS: ${strat.backtest_sharpe}\nInformation Coeff: ${strat.ic}`);
    }
  };

  function updateUI() {
    renderIncubatorTable();
    renderAutopsies();
    renderNiches();
    renderLogs();
    
    // Actualizar KPIs
    const liveCount = appState.strategies.filter(s => s.status === 'LIVE').length;
    document.getElementById('val-alphas-live').innerHTML = `${liveCount} <span style="font-size: 0.9rem; color: var(--accent-cyan);">/ ${appState.strategies.length} total</span>`;
    
    const decayCount = appState.strategies.filter(s => s.status === 'ALPHA_DECAY').length;
    document.getElementById('val-decay-count').innerHTML = `${decayCount} <span style="font-size: 0.9rem; color: var(--accent-muted);">Alpha Decay</span>`;
  }

  // Inicializar
  initCharts();
  updateUI();
  fetchBackendStatus();
});
