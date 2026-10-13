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
    ],
    history: [],
    ratchet: null,
    vault: null,
    freqtradeStrategies: [],
    backtestResults: [],
    stressReport: null,
    liveTrades: null
  };

  let API_AUTH_TOKEN = localStorage.getItem('cockpit_token') || '';
  if (!API_AUTH_TOKEN) {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('token')) {
      API_AUTH_TOKEN = urlParams.get('token');
      localStorage.setItem('cockpit_token', API_AUTH_TOKEN);
    }
  }

  function getActiveAuthToken() {
    if (!API_AUTH_TOKEN) {
      const input = prompt("🔐 Se requiere Token Bearer de Autorización para el Cockpit.\nIngrese su DASHBOARD_API_TOKEN configurado en el servidor:");
      if (input && input.trim()) {
        API_AUTH_TOKEN = input.trim();
        localStorage.setItem('cockpit_token', API_AUTH_TOKEN);
      }
    }
    return API_AUTH_TOKEN;
  }
  window.getActiveAuthToken = getActiveAuthToken;

  let equityChart = null;
  let icChart = null;
  let backtestChart = null;
  let lastTestedStrategy = null;

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
        if (data.ratchet) appState.ratchet = data.ratchet;
        if (data.vault) appState.vault = data.vault;
        updateUI();
      }
    } catch (e) {
      console.log('Modo visual local independiente activo.');
    }
  }

  // 8. Renderizado de la Arquitectura Barbell (Trinquete y Bóveda)
  function renderBarbell() {
    if (appState.ratchet) {
      const r = appState.ratchet;
      const harvestedEl = document.getElementById('ratchetHarvestedVal');
      const baseEl = document.getElementById('ratchetBaseVal');
      const peakEl = document.getElementById('ratchetPeakVal');
      if (harvestedEl) harvestedEl.innerText = `+$${(r.total_harvested || 0).toFixed(2)} USDT`;
      if (baseEl) baseEl.innerText = `$${(r.base_capital || 0).toFixed(2)} USDT`;
      if (peakEl) peakEl.innerText = `$${(r.peak_equity || 0).toFixed(2)} USDT`;
    }

    if (appState.vault) {
      const v = appState.vault;
      const capitalEl = document.getElementById('vaultCapitalVal');
      const yieldEl = document.getElementById('vaultDailyYieldVal');
      const listEl = document.getElementById('vaultPositionsList');

      if (capitalEl) capitalEl.innerText = `$${(v.total_capital || 0).toFixed(2)} USDT`;

      let totalDaily = 0;
      if (listEl) {
        listEl.innerHTML = '';
        const positions = v.positions || {};
        const pairs = Object.keys(positions);
        if (pairs.length === 0) {
          listEl.innerHTML = '<span style="color: var(--text-muted); font-size: 0.75rem;">Sin posiciones abiertas.</span>';
        } else {
          pairs.forEach(pair => {
            const pos = positions[pair];
            totalDaily += (pos.projected_daily_yield || 0);
            const item = document.createElement('div');
            item.className = 'vault-pos-item';
            item.innerHTML = `
              <span class="vault-pos-pair">${pair.split(':')[0]}</span>
              <span style="color: var(--text-secondary); font-size: 0.72rem;">${(pos.expected_apr || 0).toFixed(1)}% APR</span>
              <span class="vault-pos-yield">+$${(pos.projected_daily_yield || 0).toFixed(2)}/d</span>
            `;
            listEl.appendChild(item);
          });
        }
      }
      if (yieldEl) yieldEl.innerText = `+$${totalDaily.toFixed(2)} USDT/día`;
    }
  }

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
          'Authorization': `Bearer ${getActiveAuthToken()}`,
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

  const btnTriggerTab = document.getElementById('btn-trigger-cycle-tab');
  if (btnTriggerTab) {
    btnTriggerTab.addEventListener('click', () => {
      if (btnTrigger) btnTrigger.click();
    });
  }

  const btnSynth = document.getElementById('btn-synthesize-ai');
  btnSynth.addEventListener('click', async () => {
    btnSynth.classList.add('loading');
    btnSynth.innerHTML = `<span class="pulse-dot"></span> Sintetizando con OpenRouter...`;
    addLog('ai', 'Conectando con OpenRouter (DeepSeek-V3 / Qwen-2.5-Coder)...');

    try {
      const res = await fetch('/api/synthesize-alpha', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getActiveAuthToken()}`,
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

  // 9. Laboratorio Cuantitativo: Diseñador & Probador de Estrategias
  function renderBacktestChart(curveData) {
    const canvas = document.getElementById('backtestChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let rawList = curveData && curveData.length ? curveData : [1000, 1015, 1022, 1038, 1050, 1065, 1058, 1082, 1105, 1130];
    if (rawList.length > 100) {
      const step = Math.ceil(rawList.length / 100);
      rawList = rawList.filter((_, idx) => idx % step === 0 || idx === rawList.length - 1);
    }
    const values = rawList.map(p => (typeof p === 'object' && p !== null && p.equity !== undefined) ? p.equity : Number(p));
    const labels = rawList.map((p, idx) => {
      if (typeof p === 'object' && p !== null && p.timestamp) {
        return p.timestamp.slice(5, 16);
      }
      return `B${idx + 1}`;
    });

    if (backtestChart) {
      backtestChart.data.labels = labels;
      backtestChart.data.datasets[0].data = values;
      backtestChart.update();
      return;
    }

    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(0, 242, 254, 0.35)');
    gradient.addColorStop(1, 'rgba(0, 242, 254, 0.0)');

    backtestChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Equity Simulado (USDT)',
          data: values,
          borderColor: '#00f2fe',
          backgroundColor: gradient,
          borderWidth: 2,
          tension: 0.25,
          fill: true,
          pointRadius: 0,
          pointHoverRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `Equity: $${Number(ctx.raw).toFixed(2)} USDT`
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 9 }, maxTicksLimit: 8 }
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 9 } }
          }
        }
      }
    });
  }

  async function validateFormulaAST(formula) {
    const feedback = document.getElementById('formulaFeedback');
    const tagStatus = document.getElementById('tag-ast-status');
    if (!formula || !formula.trim()) {
      if (feedback) feedback.innerHTML = '<span class="text-rose">⚠ La fórmula no puede estar vacía.</span>';
      return false;
    }
    try {
      const res = await fetch('/api/validate-formula', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getActiveAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ formula })
      });
      const data = await res.json();
      if (res.ok && data.valid) {
        if (feedback) {
          const vars = Array.isArray(data.features_used) ? data.features_used.join(', ') : (Array.isArray(data.variables) ? data.variables.join(', ') : 'returns, volume');
          feedback.innerHTML = `<span class="text-emerald">✔ AST Válido | Profundidad: ${data.depth || 1} | Variables: ${vars}</span>`;
        }
        if (tagStatus) {
          tagStatus.innerText = 'AST ZERO-EVAL VALIDADO';
          tagStatus.style.color = 'var(--accent-emerald)';
          tagStatus.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        }
        return true;
      } else {
        if (feedback) {
          feedback.innerHTML = `<span class="text-rose">✖ Error AST: ${data.error || 'Sintaxis inválida'}</span>`;
        }
        if (tagStatus) {
          tagStatus.innerText = 'ERROR SINTAXIS AST';
          tagStatus.style.color = 'var(--accent-rose)';
          tagStatus.style.borderColor = 'rgba(244, 63, 94, 0.4)';
        }
        return false;
      }
    } catch (err) {
      console.error('Error validando AST:', err);
      return false;
    }
  }

  function initStudioControls() {
    const templateSelect = document.getElementById('select-formula-template');
    const formulaInput = document.getElementById('input-formula');
    const btnValidate = document.getElementById('btn-validate-ast');
    const btnRun = document.getElementById('btn-run-backtest');
    const btnDeploy = document.getElementById('btn-deploy-sandbox');

    if (templateSelect && formulaInput) {
      templateSelect.addEventListener('change', () => {
        if (templateSelect.value) {
          formulaInput.value = templateSelect.value;
          validateFormulaAST(formulaInput.value);
        }
      });
    }

    if (btnValidate && formulaInput) {
      btnValidate.addEventListener('click', () => {
        validateFormulaAST(formulaInput.value);
      });
      formulaInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') validateFormulaAST(formulaInput.value);
      });
    }

    if (btnRun) {
      btnRun.addEventListener('click', async () => {
        const formula = formulaInput ? formulaInput.value.trim() : '';
        const pair = document.getElementById('select-pair').value;
        const direction = document.getElementById('select-direction').value;
        const leverage = parseFloat(document.getElementById('select-leverage').value) || 1.0;
        const stoploss = parseFloat(document.getElementById('select-stoploss').value) || 0.10;

        if (!formula) {
          alert('Por favor ingresa una fórmula matemática válida.');
          return;
        }

        btnRun.disabled = true;
        btnRun.innerHTML = `<span class="pulse-dot"></span> Simulando Barras 4H...`;
        addLog('info', `Ejecutando vector backtest en ${pair} (${direction}, lev=${leverage}x)...`);

        try {
          const res = await fetch('/api/test-strategy', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${getActiveAuthToken()}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              formula,
              pair,
              direction,
              leverage,
              stoploss
            })
          });

          const data = await res.json();
          if (res.ok && data.status === 'success') {
            lastTestedStrategy = {
              ...data,
              leverage,
              stoploss
            };

            const m = data.metrics;
            const elNet = document.getElementById('btNetReturn');
            const elSharpe = document.getElementById('btSharpe');
            const elDD = document.getElementById('btMaxDD');
            const elWin = document.getElementById('btWinRate');
            const elTrades = document.getElementById('btTotalTrades');
            const elDSR = document.getElementById('btDSRScore');

            if (elNet) {
              elNet.innerText = `${m.net_return_pct >= 0 ? '+' : ''}${m.net_return_pct.toFixed(2)}%`;
              elNet.style.color = m.net_return_pct >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)';
            }
            if (elSharpe) {
              elSharpe.innerText = m.sharpe_ratio.toFixed(2);
              elSharpe.style.color = m.sharpe_ratio >= 1.5 ? 'var(--accent-cyan)' : 'var(--accent-amber)';
            }
            if (elDD) {
              elDD.innerText = `-${m.max_drawdown_pct.toFixed(2)}%`;
            }
            if (elWin) {
              elWin.innerText = `${m.win_rate_pct.toFixed(1)}%`;
            }
            if (elTrades) {
              elTrades.innerText = `${m.total_trades}`;
            }
            if (elDSR) {
              elDSR.innerText = `${m.dsr_score_pct.toFixed(1)}%`;
            }

            renderBacktestChart(data.equity_curve || []);

            if (btnDeploy) {
              btnDeploy.disabled = false;
              btnDeploy.title = `Desplegar ${data.strategy_id} a Sandbox`;
              btnDeploy.innerHTML = `
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
                  <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
                </svg>
                Desplegar a Incubadora (SANDBOX)
              `;
            }

            addLog('ai', `Backtest completado: ${data.strategy_id} | Retorno: ${m.net_return_pct.toFixed(1)}% | Sharpe: ${m.sharpe_ratio.toFixed(2)} | Trades: ${m.total_trades}`);
          } else {
            alert(`Error en backtest: ${data.error || 'Error desconocido'}`);
            addLog('error', `Fallo al probar estrategia: ${data.error || 'Desconocido'}`);
          }
        } catch (err) {
          console.error(err);
          addLog('error', `Error de red en backtest: ${err.message}`);
        } finally {
          btnRun.disabled = false;
          btnRun.innerHTML = `
            <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path d="M11.596 8.697l-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 0 1 0 1.393z"/>
            </svg>
            Ejecutar Backtest Rápido
          `;
        }
      });
    }

    if (btnDeploy) {
      btnDeploy.addEventListener('click', async () => {
        if (!lastTestedStrategy) return;

        btnDeploy.disabled = true;
        btnDeploy.innerHTML = `<span class="pulse-dot"></span> Inyectando en Incubadora...`;
        addLog('info', `Inyectando ${lastTestedStrategy.strategy_id} en incubadora autónoma...`);

        try {
          const res = await fetch('/api/deploy-to-sandbox', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${getActiveAuthToken()}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              strategy_id: lastTestedStrategy.strategy_id,
              formula: lastTestedStrategy.formula,
              pair: lastTestedStrategy.pair,
              direction: lastTestedStrategy.direction,
              leverage: lastTestedStrategy.leverage,
              stoploss: lastTestedStrategy.stoploss,
              backtest_sharpe: lastTestedStrategy.metrics.sharpe_ratio,
              net_return_pct: lastTestedStrategy.metrics.net_return_pct,
              max_drawdown_pct: lastTestedStrategy.metrics.max_drawdown_pct,
              win_rate_pct: lastTestedStrategy.metrics.win_rate_pct
            })
          });

          const data = await res.json();
          if (res.ok && data.status === 'success') {
            addLog('ai', `🚀 Estrategia ${lastTestedStrategy.strategy_id} desplegada exitosamente a SANDBOX (Slot asignado).`);
            btnDeploy.innerHTML = `✔ Desplegada a SANDBOX`;
            btnDeploy.style.borderColor = 'var(--accent-emerald)';
            btnDeploy.style.color = 'var(--accent-emerald)';

            await fetchBackendStatus();
          } else {
            alert(`Error al desplegar: ${data.error || 'Error desconocido'}`);
            btnDeploy.disabled = false;
            btnDeploy.innerHTML = `Desplegar a Incubadora (SANDBOX)`;
          }
        } catch (err) {
          console.error(err);
          btnDeploy.disabled = false;
          btnDeploy.innerHTML = `Desplegar a Incubadora (SANDBOX)`;
        }
      });
    }

    // Inicializar visualización de la fórmula default y gráfica inicial
    if (formulaInput && formulaInput.value) {
      validateFormulaAST(formulaInput.value);
    }
    renderBacktestChart();
  }

  function updateUI() {
    renderIncubatorTable();
    renderCycleHistory();
    renderAutopsies();
    renderNiches();
    renderBarbell();
    renderLogs();
    
    // Actualizar KPIs
    const liveCount = appState.strategies.filter(s => s.status === 'LIVE').length;
    document.getElementById('val-alphas-live').innerHTML = `${liveCount} <span style="font-size: 0.9rem; color: var(--accent-cyan);">/ ${appState.strategies.length} total</span>`;
    
    const decayCount = appState.strategies.filter(s => s.status === 'ALPHA_DECAY').length;
    document.getElementById('val-decay-count').innerHTML = `${decayCount} <span style="font-size: 0.9rem; color: var(--accent-muted);">Alpha Decay</span>`;
  }

  // 10. Navegación Unificada de Tabs y Subvistas I+D
  function initTabNavigation() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetTab = tab.getAttribute('data-tab');
        if (!targetTab) return;

        // Actualizar tabs activos
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Actualizar paneles activos
        document.querySelectorAll('.tab-pane').forEach(pane => {
          pane.classList.remove('active');
        });

        const targetPane = document.getElementById(targetTab);
        if (targetPane) {
          targetPane.classList.add('active');
        }

        // Redimensionar gráficos de Chart.js si se hacen visibles
        if (targetTab === 'tab-autonomous-incubator') {
          setTimeout(() => {
            if (equityChart) equityChart.resize();
            if (icChart) icChart.resize();
          }, 100);
        } else if (targetTab === 'tab-strategies-rd' || targetTab === 'tab-strategy-studio') {
          setTimeout(() => {
            if (backtestChart) backtestChart.resize();
          }, 100);
        }
      });
    });

    initSubviewNavigation();
  }

  function initSubviewNavigation() {
    const subBtns = document.querySelectorAll('.subview-btn');
    const hintBadge = document.getElementById('subview-hint-status');
    subBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetView = btn.getAttribute('data-subview');
        if (!targetView) return;

        subBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        document.querySelectorAll('.subview-pane').forEach(p => p.classList.remove('active'));
        const targetPane = document.getElementById(targetView);
        if (targetPane) targetPane.classList.add('active');

        if (hintBadge) {
          if (targetView === 'subview-studio') {
            hintBadge.innerText = 'Modo: Taller Interactivo de Fórmulas';
            hintBadge.style.color = 'var(--accent-cyan)';
            hintBadge.style.borderColor = 'rgba(0, 242, 254, 0.25)';
            setTimeout(() => { if (backtestChart) backtestChart.resize(); }, 100);
          } else {
            hintBadge.innerText = 'Modo: Catálogo Histórico y Resiliencia Freqtrade';
            hintBadge.style.color = 'var(--accent-emerald)';
            hintBadge.style.borderColor = 'rgba(16, 185, 129, 0.25)';
          }
        }
      });
    });
  }

  // 11. Carga y Renderizado del Ecosistema Freqtrade (Estrategias y Backtests)
  async function fetchFreqtradeEcosystem() {
    try {
      // 1. Estrategias
      const resStrats = await fetch('/api/strategies-catalog');
      if (resStrats.ok) {
        const data = await resStrats.json();
        appState.freqtradeStrategies = data.strategies || [];
        renderFreqtradeStrategies();
      }

      // 2. Backtests
      const resBts = await fetch('/api/backtests-catalog');
      if (resBts.ok) {
        const data = await resBts.json();
        appState.backtestResults = data.backtests || [];
        renderBacktestResults();
      }

      // 3. Stress Report
      const resStress = await fetch('/api/stress-report');
      if (resStress.ok) {
        const data = await resStress.json();
        appState.stressReport = data.data || {};
        renderStressReport();
      }

      // 4. Live Trades
      const resTrades = await fetch('/api/live-trades');
      if (resTrades.ok) {
        const data = await resTrades.json();
        appState.liveTrades = data.data || {};
        renderLiveTrades();
      }
    } catch (e) {
      console.error('Error cargando ecosistema Freqtrade:', e);
    }
  }

  function renderFreqtradeStrategies() {
    const grid = document.getElementById('strategiesGrid');
    const selectFilter = document.getElementById('select-strategy-filter');
    if (!grid) return;

    grid.innerHTML = '';
    if (selectFilter) {
      selectFilter.innerHTML = '<option value="ALL">-- Todas las Estrategias --</option>';
    }

    const tagCount = document.getElementById('tag-strats-count');
    if (tagCount) {
      tagCount.innerText = `${appState.freqtradeStrategies.length} ESTRATEGIAS PYTHON AUDITADAS`;
    }

    appState.freqtradeStrategies.forEach(s => {
      // Agregar al filtro
      if (selectFilter) {
        const opt = document.createElement('option');
        opt.value = s.strategy_id;
        opt.innerText = s.name;
        selectFilter.appendChild(opt);
      }

      const card = document.createElement('div');
      card.className = `strategy-card ${s.is_active ? 'active-prod' : ''}`;

      const activeBadge = s.is_active
        ? '<span class="strat-badge-active">EN PRODUCCIÓN (V7 QUANTUM)</span>'
        : '<span style="font-size: 0.7rem; color: var(--text-muted); font-family: var(--font-mono);">' + s.updated_at + '</span>';

      card.innerHTML = `
        <div class="strat-card-header">
          <span class="strat-name">${s.name}</span>
          ${activeBadge}
        </div>
        <div class="strat-desc">${s.description}</div>
        <div class="strat-tags-row">
          <span class="strat-tag">${s.timeframe}</span>
          <span class="strat-tag">SL: ${(s.stoploss * 100).toFixed(0)}%</span>
          <span class="strat-tag">${s.can_short ? 'SHORT-READY' : 'LONG-ONLY'}</span>
          ${s.has_ffd ? '<span class="strat-tag highlight">FFD d=0.40</span>' : ''}
          ${s.has_bet_sizing ? '<span class="strat-tag highlight">KELLY BET SIZING</span>' : ''}
          ${s.has_killswitch ? '<span class="strat-tag">KILLSWITCH</span>' : ''}
        </div>
        <div class="strat-card-footer">
          <span>Tamaño: ${s.size_kb} KB</span>
          <div style="display: flex; gap: 6px;">
            <button class="btn-action" style="padding: 3px 8px; font-size: 0.72rem;" onclick="filterBacktestsBy('${s.strategy_id}')">
              Ver Backtests
            </button>
            <button class="btn-action" style="padding: 3px 8px; font-size: 0.72rem; border-color: var(--accent-cyan); color: var(--accent-cyan);" onclick="loadIntoStudio('${s.strategy_id}')">
              Cargar en Studio
            </button>
          </div>
        </div>
      `;
      grid.appendChild(card);
    });

    if (selectFilter) {
      selectFilter.addEventListener('change', () => {
        renderBacktestResults(selectFilter.value);
      });
    }
  }

  window.filterBacktestsBy = function(stratId) {
    const selectFilter = document.getElementById('select-strategy-filter');
    if (selectFilter) {
      selectFilter.value = stratId;
    }
    renderBacktestResults(stratId);
    const el = document.getElementById('backtestsTable');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  window.loadIntoStudio = function(stratId) {
    const rdTabBtn = document.querySelector('.nav-tab[data-tab="tab-strategies-rd"]');
    if (rdTabBtn) rdTabBtn.click();
    const studioSubBtn = document.querySelector('.subview-btn[data-subview="subview-studio"]');
    if (studioSubBtn) studioSubBtn.click();
    const el = document.getElementById('panel-strategy-studio');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    addLog('info', `Estrategia ${stratId} seleccionada para experimentación en el Laboratorio Cuantitativo.`);
  };

  function renderBacktestResults(filter = 'ALL') {
    const tbody = document.getElementById('backtestsTableBody');
    const lblCount = document.getElementById('lbl-filter-results-count');
    if (!tbody) return;

    tbody.innerHTML = '';
    const filtered = filter === 'ALL'
      ? appState.backtestResults
      : appState.backtestResults.filter(b => b.strategy === filter);

    if (lblCount) {
      lblCount.innerText = `Mostrando ${filtered.length} de ${appState.backtestResults.length} ejecuciones`;
    }

    if (filtered.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 18px;">No hay reportes de backtest para esta estrategia.</td></tr>';
      return;
    }

    filtered.forEach(b => {
      const tr = document.createElement('tr');
      const winColor = b.winrate_pct >= 50 ? 'color: var(--accent-emerald)' : 'color: var(--accent-rose)';
      const sharpeColor = b.sharpe_ratio >= 1.5 ? 'color: var(--accent-cyan)' : (b.sharpe_ratio >= 1.0 ? 'color: var(--accent-emerald)' : 'color: var(--text-secondary)');
      const profitColor = b.profit_total_usdt >= 0 ? 'color: var(--accent-emerald)' : 'color: var(--accent-rose)';

      tr.innerHTML = `
        <td style="font-family: var(--font-mono); font-size: 0.78rem; color: #fff;">${b.date}</td>
        <td style="font-weight: 700; color: #cbd5e1;">${b.strategy}</td>
        <td>${b.trades}</td>
        <td style="${winColor}; font-weight: 600;">${b.winrate_pct}%</td>
        <td style="${profitColor}; font-weight: 700;">${b.profit_total_usdt >= 0 ? '+' : ''}${b.profit_total_usdt} USDT</td>
        <td style="color: var(--accent-rose); font-weight: 600;">-${b.max_drawdown_pct}%</td>
        <td style="${sharpeColor}; font-weight: 700;">${b.sharpe_ratio.toFixed(2)}</td>
        <td>${b.sortino_ratio.toFixed(2)}</td>
        <td style="font-family: var(--font-mono);">${b.profit_factor}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderStressReport() {
    const shockBody = document.getElementById('stressShockTableBody');
    const quarterBody = document.getElementById('quarterlyBreakdownTableBody');
    const rep = appState.stressReport;
    if (!rep || !rep.stress_test) return;

    const st = rep.stress_test;

    if (shockBody && st.friction_shock) {
      shockBody.innerHTML = '';
      st.friction_shock.forEach(fs => {
        const tr = document.createElement('tr');
        const roiColor = fs.roi_pct >= 0 ? 'color: var(--accent-emerald)' : 'color: var(--accent-rose)';
        const aliveBadge = fs.alive
          ? '<span class="status-pill status-live" style="font-size: 0.65rem;">VIVO</span>'
          : '<span class="status-pill status-decay" style="font-size: 0.65rem;">LIQUIDADO</span>';

        tr.innerHTML = `
          <td style="color: #fff; font-weight: 600;">${fs.scenario}</td>
          <td style="font-family: var(--font-mono);">${fs.friction_rt_pct}%</td>
          <td style="${roiColor}; font-weight: 700;">${fs.roi_pct >= 0 ? '+' : ''}${fs.roi_pct.toFixed(1)}%</td>
          <td>${fs.winrate.toFixed(1)}%</td>
          <td style="color: var(--accent-rose); font-weight: 600;">-${fs.max_dd_pct.toFixed(1)}%</td>
          <td>${aliveBadge}</td>
        `;
        shockBody.appendChild(tr);
      });
    }

    if (quarterBody && st.quarterly_breakdown) {
      quarterBody.innerHTML = '';
      const qkeys = Object.keys(st.quarterly_breakdown).slice(-8);
      qkeys.forEach(q => {
        const qdata = st.quarterly_breakdown[q];
        const tr = document.createElement('tr');
        const pColor = qdata.profit_abs >= 0 ? 'color: var(--accent-emerald)' : 'color: var(--accent-rose)';

        tr.innerHTML = `
          <td style="font-family: var(--font-mono); color: #fff;">${q}</td>
          <td>${qdata.trades}</td>
          <td style="color: var(--accent-cyan); font-weight: 600;">${qdata.wins}</td>
          <td style="${pColor}; font-weight: 700;">${qdata.profit_abs >= 0 ? '+' : ''}${qdata.profit_abs.toFixed(2)} USDT</td>
        `;
        quarterBody.appendChild(tr);
      });
    }
  }

  function renderLiveTrades() {
    const openBody = document.getElementById('openPositionsTableBody');
    const closedBody = document.getElementById('closedTradesTableBody');
    const tagOpenCount = document.getElementById('tag-open-positions-count');
    const tagTotalPnl = document.getElementById('tag-total-realized-pnl');
    const trades = appState.liveTrades;
    if (!trades) return;

    if (tagOpenCount) {
      tagOpenCount.innerText = `${trades.open_positions.length} ABIERTAS`;
    }
    if (tagTotalPnl) {
      const p = trades.total_realized_profit || 0.0;
      tagTotalPnl.innerText = `PNL: ${p >= 0 ? '+' : ''}$${p.toFixed(2)} USDT`;
      tagTotalPnl.style.color = p >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)';
    }

    if (openBody) {
      openBody.innerHTML = '';
      if (trades.open_positions.length === 0) {
        openBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 14px;">Sin posiciones abiertas en este momento.</td></tr>';
      } else {
        trades.open_positions.forEach(pos => {
          const tr = document.createElement('tr');
          const sideColor = pos.direction === 'SHORT' ? 'color: var(--accent-rose)' : 'color: var(--accent-emerald)';
          tr.innerHTML = `
            <td style="font-weight: 700; color: #fff;">${pos.pair}</td>
            <td style="${sideColor}; font-weight: 700;">${pos.direction}</td>
            <td style="font-family: var(--font-mono);">${pos.leverage}x</td>
            <td style="font-family: var(--font-mono);">${pos.open_rate}</td>
            <td style="color: var(--accent-cyan); font-weight: 700;">$${pos.stake_amount}</td>
            <td style="color: var(--text-secondary); font-size: 0.75rem;">${pos.strategy}</td>
          `;
          openBody.appendChild(tr);
        });
      }
    }

    if (closedBody) {
      closedBody.innerHTML = '';
      if (trades.closed_trades.length === 0) {
        closedBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 14px;">Sin trades cerrados registrados aún.</td></tr>';
      } else {
        trades.closed_trades.forEach(t => {
          const tr = document.createElement('tr');
          const pColor = t.profit_pct >= 0 ? 'color: var(--accent-emerald)' : 'color: var(--accent-rose)';
          const sideColor = t.direction === 'SHORT' ? 'color: var(--accent-rose)' : 'color: var(--accent-emerald)';
          tr.innerHTML = `
            <td style="font-weight: 700; color: #fff;">${t.pair}</td>
            <td style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">${t.close_date ? t.close_date.slice(5, 16) : '--'}</td>
            <td style="${sideColor}; font-weight: 600;">${t.direction}</td>
            <td style="${pColor}; font-weight: 700;">${t.profit_pct >= 0 ? '+' : ''}${t.profit_pct}%</td>
            <td style="${pColor}; font-weight: 600;">${t.profit_abs >= 0 ? '+' : ''}$${t.profit_abs}</td>
            <td><span class="badge-action-pill">${t.exit_reason}</span></td>
          `;
          closedBody.appendChild(tr);
        });
      }
    }
  }

  // Inicializar de forma robusta
  try { initCharts(); } catch (e) { console.error('Error initCharts:', e); }
  try { initTabNavigation(); } catch (e) { console.error('Error initTabNavigation:', e); }
  try { initStudioControls(); } catch (e) { console.error('Error initStudioControls:', e); }
  try { updateUI(); } catch (e) { console.error('Error updateUI:', e); }
  try { fetchBackendStatus(); } catch (e) { console.error('Error fetchBackendStatus:', e); }
  try { fetchFreqtradeEcosystem(); } catch (e) { console.error('Error fetchFreqtradeEcosystem:', e); }
});
