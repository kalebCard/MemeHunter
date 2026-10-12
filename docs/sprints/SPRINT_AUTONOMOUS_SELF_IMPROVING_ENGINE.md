# Sprint Backlog: Transformación a Motor Cuantitativo Auto-Evolutivo
**Proyecto:** MemeHunter Quant Platform  
**Sprint Name:** Sprint 1 — *Autonomous Alpha Loop & Self-Healing Engine*  
**Duración:** 2 semanas (10 días hábiles)  
**Velocidad Estimada:** 38 Story Points (SP)  
**Scrum Master / Lead Quant Engineer:** Antigravity  

---

## 1. Sprint Goal (Objetivo del Sprint)

> *"Implementar el bucle cerrado de auto-mejora continua mediante un monitor de salud de alphas en tiempo real (IC Decay & CUSUM), un demonio asíncrono de minería genética 24/7 y la automatización de la incubadora de estrategias sin intervención humana."*

---

## 2. Sprint Backlog & User Stories

### Épica 1: Monitoreo de Salud y Detección de Alpha Decay (13 SP)

#### US-1.1: Monitor de Information Coefficient (IC) Rodante y Tracking Error
- **Estimación:** 5 SP
- **Descripción:** Como *Quantitative Researcher*, quiero calcular el IC (Rank Information Coefficient) y el IC_IR en ventanas móviles de ejecución en vivo/paper para detectar la pérdida de poder predictivo de los factores en producción.
- **Criterios de Aceptación:**
  - [ ] Implementar clase `AlphaHealthMonitor` que reciba señales históricas y retornos realizados.
  - [ ] Calcular IC rodante (Spearman correlation) sobre ventanas configurables ($N=100, 250$ barras).
  - [ ] Almacenar series de IC e IC_IR en base de datos/JSON con marcas de tiempo.
  - [ ] Cobertura de pruebas unitarias $\ge 90\%$.

#### US-1.2: Detector de Rupturas de Régimen con Algoritmo CUSUM
- **Estimación:** 8 SP
- **Descripción:** Como *Risk Manager*, quiero detectar automáticamente quiebres estructurales en la volatilidad y distribución de retornos para saber cuándo las condiciones de mercado invalidan los modelos vigentes.
- **Criterios de Aceptación:**
  - [ ] Implementar detector CUSUM (Page-Hinkley / Cumulative Sum) bidireccional sobre retornos de estrategia y spread efectivo.
  - [ ] Disparar eventos de alerta con severidad (`INFO`, `WARNING`, `CRITICAL_BREAK`).
  - [ ] Integrar prueba de Kolmogorov-Smirnov de ventana deslizante para detectar *data drift*.
  - [ ] Test de estrés con datos sintéticos de cambio de régimen.

---

### Épica 2: Demonio de Minería Genética Continua en Segundo Plano (13 SP)

#### US-2.1: Worker Asíncrono de Minería 24/7 (`AlphaMinerDaemon`)
- **Estimación:** 8 SP
- **Descripción:** Como *Platform Engineer*, quiero un servicio en segundo plano que ejecute ciclos de minería NSGA-II programados o disparados por eventos de degradación.
- **Criterios de Aceptación:**
  - [ ] Crear script/servicio daemon que consuma las últimas Dollar Bars generadas.
  - [ ] Permitir ejecución programada (ej. cada medianoche o cada $X$ barras) o bajo demanda por trigger de CUSUM.
  - [ ] Ejecución en hilo/proceso no bloqueante con control de memoria y CPU.
  - [ ] Manejo de señales de parada segura (`SIGINT`, `SIGTERM`).

#### US-2.2: Catálogo de Diversidad de Alphas (Quality-Diversity Archive)
- **Estimación:** 5 SP
- **Descripción:** Como *Portfolio Manager*, quiero que la fábrica no solo guarde los factores con mejor Sharpe, sino un archivo diverso clasificado por nichos (horizonte temporal vs sensibilidad a volumen) para evitar factores redundantes.
- **Criterios de Aceptación:**
  - [ ] Implementar filtrado de similitud fenotípica (matriz de correlación de señales $< 0.50$).
  - [ ] Clasificar factores en celdas de nicho (ej. *Volumen-HighFreq*, *Trend-MidFreq*, *Microstructure-Reversion*).
  - [ ] Persistencia atómica de la biblioteca en disco con control de versiones.

---

### Épica 3: Incubadora Autónoma y Auto-Rebalanceo (12 SP)

#### US-3.1: Conexión Estado-Evento de la Incubadora (`AutonomousLifecycleTrigger`)
- **Estimación:** 7 SP
- **Descripción:** Como *Head of Trading*, quiero que las estrategias sean promovidas o degradadas automáticamente entre `Paper`, `Canary`, `Production`, `Quarantine` y `Deprecated` según sus métricas de ejecución.
- **Criterios de Aceptación:**
  - [ ] Si una estrategia en `Production` supera un Drawdown $> 2\sigma$ del backtest o su IC se vuelve negativo durante 30 barras consecutivas $\rightarrow$ Mover automáticamente a `Quarantine`.
  - [ ] Si un candidato en `Paper` mantiene Sharpe OOS $> 1.5$ y pasa CPCV con $PBO < 0.15$ durante el período de prueba $\rightarrow$ Promover automáticamente a `Canary`.
  - [ ] Registro de auditoría inmutable de todas las transiciones de estado con motivo y métricas causales.

#### US-3.2: Re-ponderación Dinámica de Portafolio con HRP Online
- **Estimación:** 5 SP
- **Descripción:** Como *Portfolio Allocator*, quiero recalcular los pesos de capital usando Hierarchical Risk Parity cada vez que un factor es promovido o enviado a cuarentena.
- **Criterios de Aceptación:**
  - [ ] Invocar `HierarchicalRiskParityAllocator` excluyendo factores en cuarentena.
  - [ ] Aplicar filtros de rotación para evitar sobre-operar (turnover constraint $\le 20\%$ por rebalanceo).
  - [ ] Generar nuevo vector de pesos normalizado a 1.0 (100% notional).

---

## 3. Definition of Done (DoD)

Para que cualquier historia de usuario se considere "Done", debe cumplir:
1. **Código y Tipado:** Cumplir con PEP 8, anotaciones de tipos completas (`typing`) y docstrings en español o inglés técnico.
2. **Testing:** Pruebas unitarias e integrales en `pytest` con cobertura mínima del 85% para nuevos módulos.
3. **Validación Cuantitativa:** Ningún cambio algorítmico puede relajar los filtros de CPCV, PBO ($<0.15$) ni control FDR Benjamini-Hochberg.
4. **Resiliencia:** Manejo robusto de excepciones; el fallo de un factor no debe detener el pipeline de ejecución ni la fábrica.
5. **Documentación:** Actualización de la documentación técnica en `docs/` y registro en el manual unificado.

---

## 4. Cronograma del Sprint (10 Días)

| Días | Actividades Principales | Entregables |
| :--- | :--- | :--- |
| **Días 1 - 3** | Implementación de `AlphaHealthMonitor` y detector CUSUM (US-1.1, US-1.2). | Módulo de monitoreo de métricas y tests unitarios. |
| **Días 4 - 6** | Creación del demonio `AlphaMinerDaemon` y archivo de diversidad (US-2.1, US-2.2). | Servicio background ejecutable con soporte CLI y logging estructurado. |
| **Días 7 - 8** | Automatización de la incubadora y disparadores de transición de estado (US-3.1). | Máquina de estados autónoma vinculada al monitor de salud. |
| **Día 9** | Integración del rebalanceo HRP dinámico y circuito de fin de ciclo (US-3.2). | Bucle cerrado E2E funcional. |
| **Día 10** | Pruebas E2E de simulación (stress testing de degradación forzada) y Sprint Review. | Demostración del ciclo completo de auto-recuperación y release. |

---

## 5. Matriz de Riesgos del Sprint

| Riesgo | Severidad | Mitigación |
| :--- | :--- | :--- |
| **Sobre-ajuste en la minería continua (Overfitting Drift)** | ALTA | Mantener las particiones CPCV purgadas con embargo estricto y cuota FDR máxima en cada ciclo. |
| **Consumo excesivo de recursos por el daemon** | MEDIA | Limitar el pool de procesos de NSGA-II a $N-2$ cores y pausar minería si la CPU supera el 85%. |
| **Rebalanceo errático de portafolio (Churling)** | MEDIA | Implementar banda de inercia (hysteresis band) y restricción de rotación en el HRP. |
