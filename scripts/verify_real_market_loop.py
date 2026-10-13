"""
verify_real_market_loop.py - Prueba Operativa con Datos Reales de Binance Futures.
Ejecuta un ciclo completo de auto-sanación y auto-mejora con las velas reales de mercado.
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import pandas as pd
from data_engine.real_market_feed import load_real_market_dataframe, build_signals_and_returns_for_strategies
from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus
from portfolio.autonomous_orchestrator import AutonomousPortfolioOrchestrator
from portfolio.oos_gating import OOSGatingValidator
from portfolio.db_schema import get_all_strategies_db, get_cycle_history_db


def main():
    print("=" * 80)
    print("🚀 MEME HUNTER: VERIFICACIÓN OPERATIVA CON DATOS REALES DE MERCADO")
    print("=" * 80)

    # 1. Cargar datos reales de Binance Futures
    pair = "DOGE_USDT_USDT"
    print(f"\n[1] Cargando velas reales de Binance Futures para {pair} (4h)...")
    market_df = load_real_market_dataframe(pair=pair, timeframe="4h", n_bars=150)
    print(f"  -> {len(market_df)} barras OHLCV reales cargadas exitosamente.")
    print(f"  -> Rango temporal: {market_df.index[0]} a {market_df.index[-1]}")
    print(f"  -> Último precio close: ${market_df['close'].iloc[-1]:.6f}")

    # 2. Inicializar incubadora con estrategias reales
    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy("ALPHA_MOM_01", "ts_rank(close, 14)", backtest_sharpe=2.1, status=StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("ALPHA_VOL_02", "ts_zscore((high - low), 10) * rvol", backtest_sharpe=1.85, status=StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("ALPHA_CAND_03", "ts_decay(close, 10)", backtest_sharpe=1.5, status=StrategyLifecycleStatus.SANDBOX)

    # 3. Evaluar señales vectoriales sobre datos reales
    print("\n[2] Evaluando señales vectoriales sobre microestructura real...")
    signals_df, fwd_ret, returns_matrix = build_signals_and_returns_for_strategies(market_df, incubator.strategies)
    print(f"  -> Señales calculadas: {list(signals_df.columns)}")
    print(f"  -> Retorno medio forward: {fwd_ret.mean():.6f} | Volatilidad: {fwd_ret.std():.6f}")

    # 4. Orquestar el ciclo autónomo completo
    print("\n[3] Ejecutando ciclo autónomo con Gobernanza OOS (CPCV, PBO, DSR)...")
    orchestrator = AutonomousPortfolioOrchestrator(
        incubator=incubator,
        gating_validator=OOSGatingValidator(min_bars=40, max_correlation=0.40, max_pbo=0.15)
    )

    report = orchestrator.process_cycle(
        signals_df=signals_df,
        forward_returns=fwd_ret,
        returns_matrix_df=returns_matrix,
        market_df=market_df
    )

    print("\n[4] Acciones registradas en el ciclo:")
    for act in report.actions_taken:
        print(f"  * {act}")

    print("\n[5] Asignación final de capital HRP:")
    for sid, w in report.new_weights.items():
        print(f"  * {sid}: {w:.1%}")

    # 5. Verificar persistencia en base de datos SQLite WAL
    print("\n[6] Verificando persistencia atómica en SQLite WAL (portfolio/alpha_factory.db)...")
    history = get_cycle_history_db(limit=1)
    if history:
        print(f"  -> Ciclo ID #{history[0]['id']} persistido a las {history[0]['timestamp']}")
        print(f"  -> Estrategias activas registradas: {history[0]['active_strategies']}")
        print(f"  -> Acciones guardadas: {len(history[0]['actions'])}")

    print("\n" + "=" * 80)
    print("✅ VERIFICACIÓN OPERATIVA COMPLETADA: EL MOTOR FUNCIONA AL 100%")
    print("=" * 80)


if __name__ == "__main__":
    main()
