"""
Orquestador del Bucle Autónomo en Tiempo Real (Live Market Feed & Auto-Healing).
Conecta Binance -> Generador de Dollar Bars -> Monitor de Salud -> Autopsia IA -> Rebalanceo HRP.
Sprint 4: Integración en Vivo.
"""

import os
import sys
import time
import logging
import pandas as pd
import numpy as np

# Configurar path raíz
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from data_engine.live_market_feed import LiveMarketFeed
from portfolio.alpha_health_monitor import AlphaHealthMonitor
from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus
from portfolio.autonomous_orchestrator import AutonomousPortfolioOrchestrator
from portfolio.alpha_autopsy import AlphaAutopsyAgent
from mining.alpha_daemon import AlphaMinerDaemon
from mining.llm_alpha_generator import LLMAlphaSynthesizer
from mining.llm_client import OpenRouterClient

logger = logging.getLogger("LiveAlphaLoop")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    print("=" * 85)
    print(" [MEMEHUNTER] INICIANDO BUCLE AUTONOMO EN TIEMPO REAL CON BINANCE SPOT")
    print("=" * 85)

    symbols = ["DOGE/USDT", "PEPE/USDT", "SHIB/USDT"]
    primary_symbol = "DOGE/USDT"

    # 1. Inicializar Incubadora
    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy("ALPHA_MOM_01", "ts_rank(close, 14)", backtest_sharpe=2.1, status=StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("ALPHA_VOL_02", "ts_zscore((high - low), 10) * rvol", backtest_sharpe=1.85, status=StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("ALPHA_DECAY_03", "ts_delay(close, 10)", backtest_sharpe=1.4, status=StrategyLifecycleStatus.LIVE)

    # 2. Inicializar Componentes Cognitivos
    llm_client = OpenRouterClient()
    autopsy_agent = AlphaAutopsyAgent(client=llm_client)
    synthesizer = LLMAlphaSynthesizer(client=llm_client)
    daemon = AlphaMinerDaemon(archive_path=os.path.join(BASE_DIR, "mining", "diversity_archive.json"))

    orchestrator = AutonomousPortfolioOrchestrator(
        incubator=incubator,
        health_monitor=AlphaHealthMonitor(rolling_window=15, min_healthy_ic=0.03),
        miner_daemon=daemon,
        autopsy_agent=autopsy_agent,
        llm_synthesizer=synthesizer
    )

    # 3. Inicializar Live Market Feed
    feed = LiveMarketFeed(
        symbols=symbols,
        notional_threshold=500_000.0,
        poll_interval_seconds=3.0
    )

    iteration_count = 0

    def on_dollar_bar_closed(symbol: str, newest_bar: pd.Series):
        nonlocal iteration_count
        iteration_count += 1
        print(f"\n⚡ [{symbol}] NUEVA DOLLAR BAR DETECTADA | Close: ${newest_bar['close']:.6f} | Vol: {newest_bar['volume']:,.0f}")

        bars_df = feed.get_latest_dollar_bars(symbol)
        if len(bars_df) < 15:
            print(f"  -> Acumulando barras ({len(bars_df)}/15 para ventana mínima de auditoría)...")
            return

        # Computar señales de los factores activos sobre las Dollar Bars reales
        fwd_returns = bars_df['returns'].shift(-1).fillna(0.0)
        
        # Evaluar factores con la data real
        sig_mom = bars_df['close'].pct_change(14).fillna(0.0)
        sig_vol = (bars_df['hl_spread'] * bars_df['rvol']).fillna(0.0)
        sig_lag = bars_df['close'].shift(10).pct_change().fillna(0.0)

        signals_df = pd.DataFrame({
            'ALPHA_MOM_01': sig_mom,
            'ALPHA_VOL_02': sig_vol,
            'ALPHA_DECAY_03': sig_lag
        }, index=bars_df.index)

        returns_matrix = pd.DataFrame({
            'ALPHA_MOM_01': sig_mom * fwd_returns,
            'ALPHA_VOL_02': sig_vol * fwd_returns,
            'ALPHA_DECAY_03': sig_lag * fwd_returns
        }, index=bars_df.index)

        print("  -> Ejecutando ciclo de auditoría cuantitativa y auto-sanación...")
        report = orchestrator.process_cycle(
            signals_df=signals_df,
            forward_returns=fwd_returns,
            returns_matrix_df=returns_matrix,
            market_df=bars_df
        )

        for act in report.actions_taken:
            print(f"     [x] {act}")

        print("  -> Distribución de Capital Actualizada (HRP):")
        for sid, w in report.new_weights.items():
            print(f"     * {sid}: {w * 100:.2f}% de capital asignado")

        # Guardar estado para que el dashboard web lo refleje automáticamente
        incubator.save_state(os.path.join(BASE_DIR, "portfolio", "incubator_state.json"))

    feed.subscribe_bar_closed(on_dollar_bar_closed)
    feed.start()

    print(f"📡 Feed en vivo conectado a Binance. Monitoreando: {', '.join(symbols)}")
    print("🖥️ El Cockpit Dashboard en http://localhost:8080 reflejará las actualizaciones en vivo.")
    print("Presiona Ctrl+C para finalizar.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo live loop...")
        feed.stop()


if __name__ == "__main__":
    main()
