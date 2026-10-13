---
id: HIST-SPRINT-002
title: "Plan Scrum Sprint 2: Motor de Investigación Cuantitativa Aumentado por IA (OpenRouter)"
category: history/sprints
version: 1.0
status: COMPLETED
last_updated: 2026-10-12
author: Quantitative Engineering & Systems Architecture Team
references:
  - docs/research/strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md
  - docs/history/INDEX_HISTORICO.md
---

# Sprint Backlog: Motor de Investigación Cuantitativa Aumentado por IA (OpenRouter)
**Proyecto:** MemeHunter Quant Platform  
**Sprint Name:** Sprint 2 — *LLM-Augmented Autonomous Research & Forensics Engine*  
**Duración:** 2 semanas (10 días hábiles)  
**Velocidad Estimada:** 36 Story Points (SP)  
**Scrum Master / Lead Quant Engineer:** Antigravity  

---

## 1. Sprint Goal (Objetivo del Sprint)

> *"Integrar OpenRouter como cerebro cognitivo en el bucle autónomo para transformar la minería combinatoria en síntesis de factores guiada por hipótesis de microestructura económica, e implementar un agente forense (Alpha Autopsy) que diagnostique la causa raíz del decaimiento de factores antes del rebalanceo del portafolio."*

---

## 2. Sprint Backlog & User Stories

### Épica 1: Conector Resiliente de OpenRouter & Compilador AST (11 SP)

#### US-2.1: Cliente Universal OpenRouter con Failover y Presupuesto de Tokens
- **Estimación:** 5 SP
- **Descripción:** Como *Platform Engineer*, quiero un cliente robusto que interactúe con la API de OpenRouter con reintentos exponenciales, control estricto de timeout, soporte multimodelo (DeepSeek-V3, Qwen-2.5-Coder, Claude 3.5 Sonnet) y modo degradado seguro (fallback offline) si la API no está disponible o falta la clave.
- **Criterios de Aceptación:**
  - [ ] Implementar clase `OpenRouterClient` con autenticación vía variable de entorno `OPENROUTER_API_KEY`.
  - [ ] Enrutamiento dinámico por modelo según la tarea (`model_fast` para síntesis masiva, `model_reasoning` para autopsias).
  - [ ] Control de costo/presupuesto de tokens diario para evitar gastos desmedidos.
  - [ ] Modo offline simulado/fallback sin romper la ejecución cuando no hay conexión.

#### US-2.2: Validador Sintáctico & Sanitizador de Expresiones Simbólicas
- **Estimación:** 6 SP
- **Descripción:** Como *Quant Developer*, quiero analizar y validar las expresiones generadas por el LLM contra el árbol de sintaxis de `AlphaGrammar` para garantizar que toda fórmula sea ejecutable, tipada y libre de alucinaciones sintácticas.
- **Criterios de Aceptación:**
  - [ ] Parser seguro que transforme strings de fórmulas del LLM a nodos `ASTNode`.
  - [ ] Rechazo estricto de llamadas no autorizadas (sandboxing de código, prohibición de `eval` o imports externos).
  - [ ] Detección y filtrado de divisiones por cero o constantes degeneradas.

---

### Épica 2: Generación Semántica de Alphas Guiada por Microestructura (13 SP)

#### US-2.3: Generador de Hipótesis de Microestructura (`LLMAlphaSynthesizer`)
- **Estimación:** 8 SP
- **Descripción:** Como *Quantitative Researcher*, quiero que el LLM proponga factores basados en conceptos financieros reales de memecoins (order flow imbalance, ratio amihud, saltos de liquidez y contracción de rango en Dollar Bars) en lugar de combinaciones aleatorias.
- **Criterios de Aceptación:**
  - [ ] Estructurar prompts con información contextual del régimen de mercado actual y de los factores en falla.
  - [ ] Salida estructurada garantizada en JSON schema (`formulas`, `economic_rationale`, `expected_holding_period`).
  - [ ] Inyección automática de las fórmulas compiladas en el pipeline de backtesting.

#### US-2.4: Mutación Guiada por IA en el Demonio de Minería (`AlphaMinerDaemon`)
- **Estimación:** 5 SP
- **Descripción:** Como *Mining Specialist*, quiero que el demonio 24/7 solicite al LLM semillas de mutación cuando la búsqueda genética estandar converja a óptimos locales o pierda diversidad.
- **Criterios de Aceptación:**
  - [ ] Si la población de NSGA-II estanca su ganancia de IC_IR durante 2 generaciones consecutivas, solicitar 5 semillas al LLM.
  - [ ] Evaluar y clasificar las fórmulas en el `QualityDiversityArchive`.

---

### Épica 3: Agente Forense de Alpha Decay & Auditoría Contextual (12 SP)

#### US-2.5: Agente Forense de Autopsia de Factores (`AlphaAutopsyAgent`)
- **Estimación:** 7 SP
- **Descripción:** Como *Risk Manager*, quiero que el sistema ejecute una autopsia cognitiva cuando un factor entra en `WARNING_DECAY` o `CRITICAL_BREAK` para entender qué condición de mercado (funding, slippage, cambio de régimen) provocó su colapso.
- **Criterios de Aceptación:**
  - [ ] Extraer un vector de métricas de fallo: IC rodante, p-valor, estadísticas de volatilidad y slippage real vs simulado.
  - [ ] Enviar el reporte al modelo de razonamiento profundo (DeepSeek-R1 / Claude 3.5 Sonnet) para obtener el dictamen forense.
  - [ ] Generar un reporte estructurado `AutopsyReport` (diagnóstico, causa raíz, recomendación de exclusión/ajuste).

#### US-2.6: Integración del Bucle Forense en `AutonomousPortfolioOrchestrator`
- **Estimación:** 5 SP
- **Descripción:** Como *System Architect*, quiero que el orquestador principal invoque la autopsia de IA de forma no bloqueante y use las recomendaciones del LLM para restringir el espacio de búsqueda del próximo ciclo de minería.
- **Criterios de Aceptación:**
  - [ ] Disparar la autopsia en hilo background para no retrasar el rebalanceo de pesos del HRP.
  - [ ] Persistir el histórico de autopsias en `portfolio/autopsies.json`.
  - [ ] Alimentar las directivas de exclusión del LLM a la siguiente consulta del `LLMAlphaSynthesizer`.

---

## 3. Definition of Done (DoD)

1. **Sandboxing de Seguridad:** Ninguna salida de texto del LLM puede ser ejecutada directamente con `exec()` o `eval()`. Todas las fórmulas deben pasar por el parser AST formal.
2. **Resiliencia ante Fallos de Red/API:** Si OpenRouter responde con código de error, agota saldo o sufre timeout ($> 30\text{s}$), el sistema debe degradar con elegancia y continuar con la minería genética tradicional sin interrumpir el trading.
3. **Validación Cuantitativa Continua:** Los factores generados por IA deben superar los mismos filtros estrictos de CPCV, PBO ($<0.15$) y FDR (Benjamini-Hochberg) que los factores genéticos.
4. **Testing Automatizado:** Cobertura de pruebas unitarias $\ge 85\%$ en `pytest`, incluyendo pruebas con mocks para evitar consumo de API keys en CI/CD.

---

## 4. Cronograma del Sprint (10 Días)

| Días | Actividades Principales | Entregables |
| :--- | :--- | :--- |
| **Días 1 - 2** | Implementación de `OpenRouterClient` y parser seguro AST (US-2.1, US-2.2). | Módulo conector probado con mocks y soporte de failover. |
| **Días 3 - 5** | Creación del `LLMAlphaSynthesizer` y mutación asistida (US-2.3, US-2.4). | Generador de hipótesis de microestructura e inyección en `QualityDiversityArchive`. |
| **Días 6 - 8** | Implementación del `AlphaAutopsyAgent` (US-2.5). | Agente de diagnóstico forense ante decaimiento de factores. |
| **Día 9** | Integración completa en el bucle cerrado del `AutonomousPortfolioOrchestrator` (US-2.6). | Bucle cuantitativo cognitivo E2E funcionando. |
| **Día 10** | Pruebas de simulación E2E de degradación forzada con diagnóstico de IA y Sprint Review. | Demostración ejecutiva del sistema auto-mejorado con IA. |

---

## 5. Matriz de Riesgos del Sprint

| Riesgo | Severidad | Mitigación |
| :--- | :--- | :--- |
| **Alucinación de código o fórmulas inválidas** | ALTA | El parser AST de `AlphaGrammar` valida tipos y operadores antes de permitir el ingreso del factor al pipeline. |
| **Agotamiento de cuota de API / Caída de OpenRouter** | MEDIA | Arquitectura desacoplada: el sistema cambia automáticamente al motor NSGA-II puro si OpenRouter falla. |
| **Latencia de respuesta del LLM ($5 - 15\text{s}$)** | MEDIA | Todas las llamadas a OpenRouter son asíncronas en background; el rebalanceo de capital por HRP ocurre de inmediato. |
| **Sobre-ajuste semántico (Overfitting a narrativa)** | ALTA | Mantener inmutables las barreras estadísticas (CPCV purgado, PBO $< 0.15$, control FDR). |
