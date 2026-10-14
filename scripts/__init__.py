"""
Meme Hunter - Quantitative & Operational Scripts Ecosystem.
Organized into 6 specialized domains:
  - scripts.research: Financial mathematics, features & statistical metrics.
  - scripts.backtest: Backtesting runners, parameter optimization & audits.
  - scripts.simulation: Monte Carlo, fat-tail bootstrap & growth models.
  - scripts.pipelines: Alpha factories, ensemble compilation & live loops.
  - scripts.data: Binance Vision downloaders & universe builders.
  - scripts.ops: Daemons, monitoring, health checks & DevOps.
"""
import sys
import importlib.util

__version__ = "8.0.0"

_LEGACY_MODULE_MAP = {
    'advanced_metrics': 'scripts.research.advanced_metrics',
    'fractional_diff': 'scripts.research.fractional_diff',
    'triple_barrier_metalabeling': 'scripts.research.triple_barrier_metalabeling',
    'regime_classifier': 'scripts.research.regime_classifier',
    'order_flow_imbalance': 'scripts.research.order_flow_imbalance',
    'statistical_significance': 'scripts.research.statistical_significance',
    'train_meta_model': 'scripts.research.train_meta_model',
    'audit_advanced_backtests': 'scripts.backtest.audit_advanced_backtests',
    'audit_funding_rates': 'scripts.backtest.audit_funding_rates',
    'audit_seasonality': 'scripts.backtest.audit_seasonality',
    'backtest_apex_omega': 'scripts.backtest.backtest_apex_omega',
    'backtest_spot_capitulation': 'scripts.backtest.backtest_spot_capitulation',
    'generate_realistic_backtest': 'scripts.backtest.generate_realistic_backtest',
    'extract_pnl_breakdown': 'scripts.backtest.extract_pnl_breakdown',
    'test_conservative_stop': 'scripts.backtest.test_conservative_stop',
    'test_stop_optimization': 'scripts.backtest.test_stop_optimization',
    'monte_carlo': 'scripts.simulation.monte_carlo',
    'fat_tail_montecarlo': 'scripts.simulation.fat_tail_montecarlo',
    'simulate_100_to_1000_montecarlo': 'scripts.simulation.simulate_100_to_1000_montecarlo',
    'simulate_exponential_growth': 'scripts.simulation.simulate_exponential_growth',
    'simulate_hybrid_barbell': 'scripts.simulation.simulate_hybrid_barbell',
    'simulate_micro_capital': 'scripts.simulation.simulate_micro_capital',
    'stress_test': 'scripts.simulation.stress_test',
    'run_alpha_factory_pipeline': 'scripts.pipelines.run_alpha_factory_pipeline',
    'run_autonomous_engine_demo': 'scripts.pipelines.run_autonomous_engine_demo',
    'run_live_alpha_loop': 'scripts.pipelines.run_live_alpha_loop',
    'compile_ensemble_strategy': 'scripts.pipelines.compile_ensemble_strategy',
    'scan_live_signals': 'scripts.pipelines.scan_live_signals',
    'evaluate_growth_loop': 'scripts.pipelines.evaluate_growth_loop',
    'verify_real_market_loop': 'scripts.pipelines.verify_real_market_loop',
    'binance_vision': 'scripts.data.binance_vision',
    'build_universe': 'scripts.data.build_universe',
    'download_target': 'scripts.data.download_target',
    'profit_ratchet_daemon': 'scripts.ops.profit_ratchet_daemon',
    'delta_neutral_vault': 'scripts.ops.delta_neutral_vault',
    'funding_arbitrage': 'scripts.ops.funding_arbitrage',
    'dex_viral_radar': 'scripts.ops.dex_viral_radar',
    'meme_sentinel': 'scripts.ops.meme_sentinel',
    'dryrun_monitor': 'scripts.ops.dryrun_monitor',
    'check_health': 'scripts.ops.check_health',
    'telegram_healthcheck': 'scripts.ops.telegram_healthcheck',
    'test_binance_connection': 'scripts.ops.test_binance_connection',
    'daily_performance': 'scripts.ops.daily_performance',
    'migrate_json_to_sqlite': 'scripts.ops.migrate_json_to_sqlite',
    'meme_cli': 'scripts.ops.meme_cli',
}


class _ScriptsLegacyFinder:
    """Redirects legacy flat imports (e.g. scripts.advanced_metrics) to categorized submodules."""
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if fullname.startswith('scripts.') and fullname.count('.') == 1:
            sub = fullname.split('.')[1]
            if sub in _LEGACY_MODULE_MAP:
                target_mod = _LEGACY_MODULE_MAP[sub]
                return importlib.util.find_spec(target_mod)
        return None


if not any(getattr(f, '__name__', '') == '_ScriptsLegacyFinder' for f in sys.meta_path):
    sys.meta_path.insert(0, _ScriptsLegacyFinder)
