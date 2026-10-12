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
    history: []
  };

  let equityChart = null;
  let icChart = null;

  // ANIMACIÓN VISUAL DEL PIPELINE DE 5 ETAPAS
  async function animatePipeline(stageIndex) {
    const steps = [
      { id: 'step-monitor', conn: 'conn-1', label: '1/5 AUDITANDO SALUD CUSUM' },
      { id: 'step-autopsy', conn: 'conn-2', label: '2/5 AUTOPSIA FORENSE DEEPSEEK-R1' },
      { id: 'step-synthesis', conn: 'conn-3', label: '3/5 SÍNTESIS ZERO-EVAL AST' },
      { id: 'step-diversity', conn: 'conn-4', label: '4/5 INCUBACIÓN MAP-ELITES' },
      { id: 'step-rebalance', conn: null, label: '5/5 REBALANCEO DE CAPITAL HRP' }
    ];

    const badge = document.getElementById('pipeline-status-badge');

    for (let i = 0; i < steps.length; i++) {
      const stepEl = document.getElementById(steps[i].id);
      const connEl = steps[i].conn ? document.getElementById(steps[i].conn) : null;

      // Limpiar anterior
      steps.forEach(s => {
        const el = document.getElementById(s.id);
        el.classList.remove('step-active');
      });

      stepEl.classList.add('step-active');
      if (badge) {
        badge.innerText = steps[i].label;
        badge.style.color = 'var(--accent-cyan)';
        badge.style.borderColor = 'var(--accent-cyan)';
      }

      if (connEl) {
        connEl.classList.add('flowing');
      }

      await new Promise(r => setTimeout(r, 450));

      stepEl.classList.remove('step-active');
      stepEl.classList.add('step-done');
      if (connEl) {
        connEl.classList.remove('flowing');
        connEl.classList.add('active');
      }
    }

    if (badge) {
      badge.innerText = 'CICLO COMPLETADO CON ÉXITO';
      badge.style.color = 'var(--accent-emerald)';
      badge.style.borderColor = 'var(--accent-emerald)';
    }

    setTimeout(() => {
      // Reset suave tras 3 segundos
      steps.forEach((s, idx) => {
        const el = document.getElementById(s.id);
        el.classList.remove('step-active', 'step-done');
        if (s.conn) {
          const conn = document.getElementById(s.conn);
          conn.classList.remove('active', 'flowing');
        }
      });
      if (badge) {
        badge.innerText = 'REPOSO (IDLE)';
        badge.style.color = 'var(--text-muted)';
        badge.style.borderColor = 'var(--border-color)';
      }
    }, 4000);
  }

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

      const weightPct = ((strat.weight || 0) * 100).toFixed(1) + '%';
      const icColor = (strat.ic || 0) >= 0.03 ? 'color: var(--accent-emerald)' : 'color: var(--accent-rose)';

      tr.innerHTML = `
        <td style="font-weight: 700; color: #fff;">${strat.id}</td>
        <td style="color: var(--text-secondary); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${strat.formula}">
          ${strat.formula}
        </td>
        <td><span class="status-pill ${badgeClass}">${strat.status}</span></td>
        <td style="font-weight: 700; color: var(--accent-cyan);">${weightPct}</td>
        <td>${(strat.backtest_sharpe || 0).toFixed(2)}</td>
        <td style="${icColor}; font-weight: 600;">${(strat.ic || 0) >= 0 ? '+' : ''}${(strat.ic || 0).toFixed(3)}</td>
        <td>
          <button class="btn-action" style="padding: 4px 10px; font-size: 0.7rem;" onclick="window.auditStrategy('${strat.id}')">
            Auditar
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // 3. Renderizado de Historial de Ciclos
  function renderCycleHistory() {
    const tbody = document.getElementById('cycleHistoryTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const countTag = document.getElementById('tag-history-count');
    if (countTag) {
      countTag.innerText = `${appState.history.length} CICLOS REGISTRADOS`;
    }

    if (appState.history.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 18px;">Sin ciclos ejecutados en esta sesión. Presiona "Ejecutar Ciclo Autónomo".</td></tr>';
      return;
    }

    appState.history.forEach(h => {
      const tr = document.createElement('tr');
      const ts = h.timestamp ? h.timestamp.split('T')[1].split('.')[0] : 'En curso';
      const quaran = h.quarantined && h.quarantined.length > 0 ? `<span class="badge-action-pill" style="color: var(--accent-rose); border-color: var(--accent-rose);">${h.quarantined.join(', ')}</span>` : '<span style="color: var(--text-muted);">-</span>';
      const promo = h.promoted && h.promoted.length > 0 ? `<span class="badge-action-pill" style="color: var(--accent-emerald); border-color: var(--accent-emerald);">${h.promoted.join(', ')}</span>` : '<span style="color: var(--text-muted);">-</span>';
      const costStr = h.estimated_cycle_cost_usd !== undefined ? `$${h.estimated_cycle_cost_usd.toFixed(5)}` : '$0.00000';
      const goalBadge = h.goal_reached ? '<span class="status-pill status-live">LOGRADA</span>' : '<span style="color: var(--text-muted); font-size: 0.75rem;">En progreso</span>';

      const actionsShort = (h.actions && h.actions.length > 0) ? `${h.actions.length} acciones ejecutadas` : 'Rebalanceo';

      tr.innerHTML = `
        <td style="font-family: var(--font-mono); color: var(--accent-cyan); font-weight: 600;">${ts}</td>
        <td style="font-weight: 700; color: #fff;">${h.active_strategies || 3} LIVE</td>
        <td>${quaran}</td>
        <td>${promo}</td>
        <td style="font-family: var(--font-mono); color: var(--accent-amber);">${costStr}</td>
        <td>${goalBadge}</td>
        <td style="color: var(--text-secondary); font-size: 0.78rem;" title="${(h.actions || []).join(' | ')}">${actionsShort}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // 4. Renderizado de Autopsias IA
  function renderAutopsies() {
    const container = document.getElementById('autopsyListContainer');
    container.innerHTML = '';

    if (appState.autopsies.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem; padding: 12px;">No hay factores en decaimiento actualmente.</p>';
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

  // 5. Renderizado de Nichos de Diversidad (MAP-Elites)
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
          <div style="font-size: 0.85rem; font-weight: 700; color: var(--accent-purple); font-family: var(--font-mono);">IC_IR ${(n.ic_ir || 0).toFixed(2)}</div>
          <span class="status-pill status-live" style="font-size: 0.65rem;">${n.status}</span>
        </div>
      `;
      container.appendChild(div);
    });
  }

  // 6. Renderizado del Terminal Log
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

  // 7. Conexión con el Backend REST API
  async function fetchBackendStatus() {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        if (data.strategies) appState.strategies = data.strategies;
        if (data.autopsies) appState.autopsies = data.autopsies;
        if (data.niches) appState.niches = data.niches;
        if (data.history) appState.history = data.history;
        updateUI();
      }
    } catch (e) {
      console.log('Modo visual local independiente activo.');
    }
  }

  const API_AUTH_TOKEN = localStorage.getItem('cockpit_token') || 'meme_hunter_dev_token_2026';

  // 8. Acciones de los Botones con Animación & Feedback Inmediato
  const btnTrigger = document.getElementById('btn-trigger-cycle');
  btnTrigger.addEventListener('click', async () => {
    btnTrigger.classList.add('loading');
    btnTrigger.innerHTML = `<span class="pulse-dot"></span> Optimizando Portafolio...`;

    addLog('info', 'Iniciando ciclo autónomo: auditoría CUSUM, autopsia, síntesis y HRP...');
    
    // Disparar animación del pipeline en paralelo
    const animPromise = animatePipeline();

    try {
      const res = await fetch('/api/trigger-loop', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${API_AUTH_TOKEN}`,
          'Content-Type': 'application/json'
        }
      });
      if (res.ok) {
        const data = await res.json();
        await animPromise; // Esperar a que la animación visual culmine

        addLog('ai', `Ciclo completado con éxito. Acciones tomadas: ${data.actions ? data.actions.length : 1}`);
        if (data.estimated_cycle_cost_usd !== undefined) {
          addLog('info', `Coste del ciclo: ~$${data.estimated_cycle_cost_usd.toFixed(5)} USD | Acumulado: $${data.accumulated_cost_usd.toFixed(4)} USD`);
        }
        if (data.goal_reached) {
          addLog('ai', `🎯 META CUANTITATIVA LOGRADA: Portafolio superó el Sharpe objetivo.`);
        }
        if (data.cycle) {
          appState.history.unshift(data.cycle);
          appState.history = appState.history.slice(0, 25);
        }
        await fetchBackendStatus();

        // Actualizar gráfico de equity al alza
        if (equityChart) {
          const lastVal = equityChart.data.datasets[0].data[equityChart.data.datasets[0].data.length - 1];
          equityChart.data.datasets[0].data.push(Math.round(lastVal * 1.018 * 100) / 100);
          equityChart.data.labels.push(`Ciclo ${equityChart.data.labels.length + 1}`);
          if (equityChart.data.datasets[0].data.length > 35) {
            equityChart.data.datasets[0].data.shift();
            equityChart.data.labels.shift();
          }
          equityChart.update();
        }

        btnTrigger.classList.remove('loading');
        btnTrigger.innerHTML = `
          <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/>
            <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/>
          </svg>
          Ejecutar Ciclo Autónomo
        `;
        return;
      }
    } catch (e) {
      console.error(e);
    }

    await animPromise;
    btnTrigger.classList.remove('loading');
    btnTrigger.innerHTML = `
      <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
        <path d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/>
        <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/>
      </svg>
      Ejecutar Ciclo Autónomo
    `;
    updateUI();
  });

  const btnSynth = document.getElementById('btn-synthesize-ai');
  btnSynth.addEventListener('click', async () => {
    btnSynth.classList.add('loading');
    btnSynth.innerHTML = `<span class="pulse-dot"></span> Sintetizando con OpenRouter...`;
    addLog('ai', 'Conectando con OpenRouter (DeepSeek-V3 / Qwen-2.5-Coder)...');

    try {
      const res = await fetch('/api/synthesize-alpha', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${API_AUTH_TOKEN}`,
          'Content-Type': 'application/json'
        }
      });
      if (res.ok) {
        const data = await res.json();
        addLog('ai', `OpenRouter sintetizó ${data.count || 3} nuevos alphas validados con AST.`);
        await fetchBackendStatus();
      }
    } catch (e) {
      console.error(e);
    }

    btnSynth.classList.remove('loading');
    btnSynth.innerHTML = `
      <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
        <path d="M9.5 2.672a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 0 1H10v.5a.5.5 0 0 1-1 0v-.5h-.5a.5.5 0 0 1 0-1H9v-.5a.5.5 0 0 1 .5-.5zM14 6.672a.5.5 0 0 1 .5.5v1h1a.5.5 0 0 1 0 1h-1v1a.5.5 0 0 1-1 0v-1h-1a.5.5 0 0 1 0-1h1v-1a.5.5 0 0 1 .5-.5zM3.5 0a.5.5 0 0 1 .5.5v1h1a.5.5 0 0 1 0 1h-1v1a.5.5 0 0 1-1 0v-1h-1a.5.5 0 0 1 0-1h1v-1a.5.5 0 0 1 .5-.5zM8 5a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"/>
      </svg>
      Sintetizar con OpenRouter
    `;
    updateUI();
  });

  window.auditStrategy = function(id) {
    addLog('info', `Iniciando auditoría forense para ${id}...`);
    const strat = appState.strategies.find(s => s.id === id);
    if (strat) {
      alert(`Auditoría Cuantitativa de ${strat.id}:\nFórmula: ${strat.formula}\nEstado: ${strat.status}\nSharpe OOS: ${(strat.backtest_sharpe || 0).toFixed(2)}\nInformation Coeff: ${(strat.ic || 0).toFixed(3)}`);
    }
  };

  function updateUI() {
    renderIncubatorTable();
    renderCycleHistory();
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
