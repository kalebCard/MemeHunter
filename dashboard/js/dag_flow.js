/**
 * Meme Hunter - Multi-Agent DAG Visual Flow & Inspector (Sprint 32 PB-111, PB-112)
 * Renderizado reactivo del grafo de inferencia en tiempo real y controles Human-in-the-Loop (HITL).
 */

(function() {
  'use strict';

  // Estado del Grafo DAG
  let dagState = {
    selectedNodeId: 'dag_orchestrator',
    pipelineActive: true,
    consensusThreshold: 0.68,
    activeLayerFilters: {
      ingestion: true,
      processing: true,
      core_execution: true
    },
    nodesData: {
      'node_price_volume': {
        name: 'Precio y Volumen',
        sub: 'WebSockets L2/L3',
        category: 'INGESTA DE DATOS',
        algorithm: 'WebSockets L2/L3 Feed',
        metric_label: 'Tasa Flujo',
        metric_value: '120 msg/s',
        latency: '1.2 ms',
        description: 'Ingesta continua de libro de órdenes Level 2 y transacciones trade-by-trade desde Binance Futures.',
        layer: 'ingestion',
        status: 'ACTIVO'
      },
      'node_news_social': {
        name: 'Noticias y Redes',
        sub: 'APIs NLP Scraping',
        category: 'INGESTA DE DATOS',
        algorithm: 'NLP Stream Parser',
        metric_label: 'Fuentes',
        metric_value: '4 Streams',
        latency: '3.5 ms',
        description: 'Scraping y normalización en tiempo real de titulares de noticias crypto, DexScreener y canales sociales.',
        layer: 'ingestion',
        status: 'ACTIVO'
      },
      'node_macro_cal': {
        name: 'Calendario Macro',
        sub: 'Eventos FED / IPC',
        category: 'INGESTA DE DATOS',
        algorithm: 'Event Horizon Guard',
        metric_label: 'Próximo Evento',
        metric_value: 'FOMC (4d)',
        latency: '0.1 ms',
        description: 'Monitoreo del calendario macroeconómico, tasas de financiación (Funding Rate) y horas de alta volatilidad.',
        layer: 'ingestion',
        status: 'ACTIVO'
      },
      'technical_analysis': {
        name: 'Análisis Técnico',
        sub: 'Cuantitativo / Micro',
        category: 'PROCESAMIENTO & RIESGO',
        algorithm: 'AST Factors + FFD d=0.40',
        metric_label: 'Score Activo',
        metric_value: '+0.42',
        latency: '4.8 ms',
        description: 'Evaluación cuantitativa de momentum rápido, memoria fraccionaria FFD y desequilibrio de libro (OFI proxy).',
        layer: 'processing',
        agent_id: 'technical_analysis',
        status: 'ACTIVO'
      },
      'sentiment_agent': {
        name: 'Agente Sentimiento',
        sub: 'FinLLM Embeddings',
        category: 'PROCESAMIENTO & RIESGO',
        algorithm: 'FinLLM + Lexical Cache',
        metric_label: 'Tono Semántico',
        metric_value: '+0.65 Bullish',
        latency: '0.4 ms',
        description: 'Interpretación semántica del tono del mercado con caché local instantánea (0ms) y score [-1.0, +1.0].',
        layer: 'processing',
        agent_id: 'sentiment_agent',
        status: 'ACTIVO'
      },
      'regime_detector': {
        name: 'Detector Régimen',
        sub: 'HMM / Volatilidad',
        category: 'PROCESAMIENTO & RIESGO',
        algorithm: 'Gaussian HMM / CUSUM',
        metric_label: 'Régimen Actual',
        metric_value: 'BULL_MOMENTUM',
        latency: '5.1 ms',
        description: 'Clasificador dinámico de regímenes de mercado (Tendencia vs Rango lateral vs Pánico) condicionando pesos.',
        layer: 'processing',
        agent_id: 'regime_detector',
        status: 'ACTIVO'
      },
      'dag_orchestrator': {
        name: 'Orquestador DAG (Enrutador de Señales)',
        sub: 'Enrutador Central de Señales',
        category: 'ORQUESTACIÓN CENTRAL',
        algorithm: 'Bayesian Fusion',
        metric_label: 'Consenso Min.',
        metric_value: '0.68 Score',
        latency: '15 ms',
        description: 'Grafo Acíclico Dirigido que sintetiza los alpha-vectors de todos los agentes, aplicando pesos dinámicos según el régimen de mercado.',
        layer: 'core_execution',
        status: 'ACTIVO'
      },
      'node_risk_manager': {
        name: 'Gestor de Riesgos',
        sub: 'Filtro VaR / Drawdown',
        category: 'GOBERNANZA DE RIESGO',
        algorithm: 'Cornish-Fisher VaR 99%',
        metric_label: 'Drawdown Actual',
        metric_value: '-4.2%',
        latency: '1.1 ms',
        description: 'Filtro de riesgo institucional: auditoría de VaR 99%, Kill-Switch (-25%) y límite de correlación cruzada (<0.40).',
        layer: 'core_execution',
        status: 'ACTIVO'
      },
      'node_execution_api': {
        name: 'API de Ejecución',
        sub: 'Broker / DMA FIX',
        category: 'NÚCLEO & EJECUCIÓN',
        algorithm: 'Maker at Bid / Market Exit',
        metric_label: 'Slippage Medio',
        metric_value: '0.012%',
        latency: '8.5 ms',
        description: 'Enlace de ejecución de órdenes en Freqtrade con modo Maker pasivo en entradas y salidas forzadas a mercado.',
        layer: 'core_execution',
        status: 'ACTIVO'
      }
    }
  };

  // ---------------------------------------------------------------------------
  // Inicialización
  // ---------------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', () => {
    initDAGEventListeners();
    fetchDAGStatus();
    selectNode('dag_orchestrator');

    // Intervalo de polling suave (5 segundos)
    setInterval(fetchDAGStatus, 5000);
  });

  // ---------------------------------------------------------------------------
  // Selección e Inspección de Nodos
  // ---------------------------------------------------------------------------
  function selectNode(nodeId) {
    dagState.selectedNodeId = nodeId;
    const node = dagState.nodesData[nodeId];
    if (!node) return;

    // Resaltar visualmente en el lienzo
    document.querySelectorAll('.dag-node-capsule').forEach(el => {
      el.classList.remove('selected');
    });
    const targetEl = document.querySelector(`.dag-node-capsule[data-node-id="${nodeId}"]`);
    if (targetEl) {
      targetEl.classList.add('selected');
    }

    // Actualizar el Panel Inspector
    const titleEl = document.getElementById('inspector-node-title');
    const catEl = document.getElementById('inspector-node-category');
    const descEl = document.getElementById('inspector-node-desc');
    const mAlgo = document.getElementById('inspector-metric-algo');
    const mCons = document.getElementById('inspector-metric-consensus');
    const mConsLabel = document.getElementById('inspector-label-consensus');
    const mLat = document.getElementById('inspector-metric-latency');

    if (titleEl) titleEl.textContent = `${node.name} ${node.sub ? `(${node.sub})` : ''}`;
    if (catEl) catEl.textContent = node.category;
    if (descEl) descEl.textContent = node.description;
    if (mAlgo) mAlgo.textContent = node.algorithm;
    if (mCons) mCons.textContent = node.metric_value;
    if (mConsLabel) mConsLabel.textContent = node.metric_label || 'Consenso Min.';
    if (mLat) mLat.textContent = node.latency;

    // Actualizar botones de control HITL
    const btnToggle = document.getElementById('hitl-node-toggle-btn');
    if (btnToggle) {
      if (node.status === 'PAUSADO') {
        btnToggle.textContent = '▶ Activar Nodo';
        btnToggle.className = 'btn-hitl activate';
      } else {
        btnToggle.textContent = '⏸ Pausar Nodo';
        btnToggle.className = 'btn-hitl pause';
      }
    }

    // Sincronizar checkboxes de leyenda
    updateLegendSelection(node.layer);
  }

  function updateLegendSelection(activeLayer) {
    const cbIng = document.getElementById('legend-cb-ingestion');
    const cbProc = document.getElementById('legend-cb-processing');
    const cbCore = document.getElementById('legend-cb-core');

    if (cbIng) cbIng.checked = (activeLayer === 'ingestion');
    if (cbProc) cbProc.checked = (activeLayer === 'processing');
    if (cbCore) cbCore.checked = (activeLayer === 'core_execution');
  }

  // ---------------------------------------------------------------------------
  // Event Listeners
  // ---------------------------------------------------------------------------
  function initDAGEventListeners() {
    // Clic en nodos del lienzo
    document.querySelectorAll('.dag-node-capsule').forEach(el => {
      el.addEventListener('click', () => {
        const nodeId = el.getAttribute('data-node-id');
        if (nodeId) selectNode(nodeId);
      });
    });

    // Control HITL: Pausar / Activar Nodo
    const btnToggle = document.getElementById('hitl-node-toggle-btn');
    if (btnToggle) {
      btnToggle.addEventListener('click', () => {
        const node = dagState.nodesData[dagState.selectedNodeId];
        if (!node) return;
        const newStatus = (node.status === 'PAUSADO') ? true : false;
        toggleNode(dagState.selectedNodeId, newStatus);
      });
    }

    // Control HITL: Ejecutar Ciclo de Inferencia Manual
    const btnCycle = document.getElementById('hitl-trigger-cycle-btn');
    if (btnCycle) {
      btnCycle.addEventListener('click', triggerManualDAGCycle);
    }

    // Slider de Consenso Mínimo
    const slider = document.getElementById('hitl-consensus-slider');
    const valText = document.getElementById('hitl-consensus-val');
    if (slider) {
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (valText) valText.textContent = `${val.toFixed(2)} Score`;
      });
      slider.addEventListener('change', (e) => {
        const val = parseFloat(e.target.value);
        setDAGConsensusThreshold(val);
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Conexión con Endpoints REST del Backend
  // ---------------------------------------------------------------------------
  async function fetchDAGStatus() {
    try {
      const resp = await fetch('/api/dag/status');
      if (!resp.ok) return;
      const data = await resp.json();
      if (!data.success) return;

      const tel = data.telemetry;
      if (tel) {
        // Actualizar Badge de Estado de Pipeline
        const badge = document.getElementById('dag-pipeline-status-badge');
        if (badge) {
          if (tel.pipeline_status === 'ACTIVE') {
            badge.innerHTML = '<span class="status-dot green"></span> PIPELINE ACTIVO';
            badge.className = 'dag-pipeline-badge active';
          } else {
            badge.innerHTML = '<span class="status-dot yellow"></span> PIPELINE PAUSADO';
            badge.className = 'dag-pipeline-badge paused';
          }
        }

        // Actualizar métricas del Orquestador
        if (dagState.nodesData['dag_orchestrator']) {
          dagState.nodesData['dag_orchestrator'].latency = `${tel.avg_latency_ms.toFixed(1)} ms`;
          dagState.nodesData['dag_orchestrator'].metric_value = `${tel.consensus_threshold.toFixed(2)} Score`;
        }

        // Actualizar estado de nodos individuales
        if (tel.nodes) {
          Object.keys(tel.nodes).forEach(aid => {
            const agentTel = tel.nodes[aid];
            if (dagState.nodesData[aid]) {
              dagState.nodesData[aid].status = agentTel.active ? 'ACTIVO' : 'PAUSADO';
              dagState.nodesData[aid].latency = `${agentTel.last_latency_ms.toFixed(1)} ms`;

              const nodeCapsule = document.querySelector(`.dag-node-capsule[data-node-id="${aid}"]`);
              if (nodeCapsule) {
                if (agentTel.active) {
                  nodeCapsule.classList.remove('paused-node');
                } else {
                  nodeCapsule.classList.add('paused-node');
                }
              }
            }
          });
        }

        // Re-refrescar el inspector si está en el nodo actual
        selectNode(dagState.selectedNodeId);
      }
    } catch (err) {
      console.warn('Error sincronizando estado DAG:', err);
    }
  }

  async function toggleNode(nodeId, active) {
    try {
      const resp = await fetch('/api/dag/toggle-node', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, active: active })
      });
      const data = await resp.json();
      if (data.success) {
        if (dagState.nodesData[nodeId]) {
          dagState.nodesData[nodeId].status = active ? 'ACTIVO' : 'PAUSADO';
        }
        selectNode(nodeId);
        fetchDAGStatus();
      }
    } catch (err) {
      console.error('Error enviando toggle de nodo:', err);
    }
  }

  async function setDAGConsensusThreshold(threshold) {
    try {
      const resp = await fetch('/api/dag/set-threshold', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ threshold: threshold })
      });
      const data = await resp.json();
      if (data.success) {
        dagState.consensusThreshold = threshold;
        if (dagState.nodesData['dag_orchestrator']) {
          dagState.nodesData['dag_orchestrator'].metric_value = `${threshold.toFixed(2)} Score`;
        }
        selectNode('dag_orchestrator');
      }
    } catch (err) {
      console.error('Error actualizando umbral de consenso:', err);
    }
  }

  async function triggerManualDAGCycle() {
    const btn = document.getElementById('hitl-trigger-cycle-btn');
    if (btn) btn.classList.add('loading');

    try {
      const resp = await fetch('/api/dag/trigger-cycle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await resp.json();
      if (data.success && data.vector) {
        const v = data.vector;
        const verd = data.verdict;

        // Feedback visual inmediato
        const flowArrow = document.getElementById('dag-vector-alpha-label');
        if (flowArrow) {
          flowArrow.innerHTML = `Vector Alpha: <strong>Score ${v.composite_score > 0 ? '+' : ''}${v.composite_score.toFixed(2)} (${v.decision})</strong>`;
          flowArrow.classList.add('flash');
          setTimeout(() => flowArrow.classList.remove('flash'), 1500);
        }

        // Actualizar inspector si el orquestador está seleccionado
        if (dagState.selectedNodeId === 'dag_orchestrator') {
          const mLat = document.getElementById('inspector-metric-latency');
          if (mLat) mLat.textContent = `${v.inference_cycle_ms.toFixed(1)} ms`;
        }

        fetchDAGStatus();
      }
    } catch (err) {
      console.error('Error disparando ciclo de inferencia:', err);
    } finally {
      if (btn) btn.classList.remove('loading');
    }
  }

})();
