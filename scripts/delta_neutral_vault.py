"""
delta_neutral_vault.py - Orquestador y Gestor de la Bóveda Segura Delta-Neutral (PB-69).

Administra el capital cosechado por el trinquete (Profit Ratchet) y ejecuta
arbitraje Cash & Carry / Delta-Neutral sistemático:
1. Recibe asignaciones de capital desde el daemon de trinquete (balance Spot/Bóveda).
2. Escanea las oportunidades de Funding Rate con mayor APR positivo y alta liquidez.
3. Modela y simula la posición de dos patas: Long Spot + Short Perpetuo 1.0x aislado.
4. Calcula el flujo de caja pasivo real (Cashflow) generado cada 8 horas sin riesgo de mercado.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
LOG = logging.getLogger("DeltaNeutralVault")

ROOT = Path(__file__).resolve().parents[1]
VAULT_STATE_FILE = ROOT / "user_data" / "vault_state.json"


class DeltaNeutralVault:
    def __init__(
        self,
        initial_capital: float = 0.0,
        min_apr_threshold: float = 12.0,   # APR mínimo para desplegar capital en un par
        max_pairs: int = 5,                # Diversificar bóveda en hasta 5 pares
        state_file: Path = VAULT_STATE_FILE
    ):
        self.state_file = state_file
        self.total_capital = initial_capital
        self.min_apr_threshold = min_apr_threshold
        self.max_pairs = max_pairs
        self.positions: Dict[str, dict] = {}
        self.total_income_collected = 0.0

        self.load_state()

    def load_state(self):
        if self.state_file and self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.total_capital = data.get("total_capital", self.total_capital)
                    self.positions = data.get("positions", {})
                    self.total_income_collected = data.get("total_income_collected", 0.0)
                    LOG.info(f"Bóveda Segura cargada: Capital={self.total_capital:.2f} USDT, Ingresos={self.total_income_collected:.2f} USDT")
            except Exception as e:
                LOG.warning(f"No se pudo cargar estado de bóveda: {e}")

    def save_state(self):
        if not self.state_file:
            return
        data = {
            "total_capital": self.total_capital,
            "positions": self.positions,
            "total_income_collected": self.total_income_collected,
            "updated_at": datetime.utcnow().isoformat()
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def deposit(self, amount: float):
        """Recibe una inyección de utilidades proveniente del trinquete de futuros."""
        if amount <= 0:
            return
        self.total_capital += amount
        LOG.info(f"💰 Depósito recibido en la Bóveda Segura: +{amount:.2f} USDT | Total Bóveda: {self.total_capital:.2f} USDT")
        self.save_state()

    def allocate_capital(self, market_opportunities: List[dict]):
        """
        Asigna el capital disponible a las mejores oportunidades delta-neutrales.
        Cada posición asigna 50% a Spot (Long) y 50% a Futuros (Short 1x aislado).
        """
        if self.total_capital <= 0 or not market_opportunities:
            return

        eligible = [o for o in market_opportunities if o.get("apr", 0) >= self.min_apr_threshold and o.get("apr", 0) > 0]
        if not eligible:
            LOG.info("No hay oportunidades de funding que superen el umbral mínimo de APR.")
            return

        top_pairs = eligible[: self.max_pairs]
        capital_per_pair = self.total_capital / len(top_pairs)

        self.positions.clear()
        for opp in top_pairs:
            sym = opp["symbol"]
            apr = opp["apr"]
            rate_8h = opp.get("funding_rate", apr / (3 * 365)) / 100.0

            # 50% Spot Long + 50% Futuros Short 1x -> Notional de la posición = capital_per_pair / 2
            notional = capital_per_pair / 2.0

            self.positions[sym] = {
                "allocated_capital": round(capital_per_pair, 2),
                "spot_long_usdt": round(notional, 2),
                "futures_short_usdt": round(notional, 2),
                "expected_apr": round(apr, 2),
                "rate_8h": rate_8h,
                "projected_daily_yield": round(notional * rate_8h * 3, 4)
            }

        LOG.info(f"Bóveda Segura diversificada en {len(self.positions)} pares delta-neutrales.")
        self.save_state()

    def simulate_settlement_cycle(self):
        """Simula el cobro de un ciclo de funding (cada 8 horas)."""
        cycle_yield = 0.0
        for sym, pos in self.positions.items():
            # El funding se cobra sobre el valor nominal del Short en futuros
            payout = pos["futures_short_usdt"] * pos["rate_8h"]
            cycle_yield += payout

        self.total_income_collected += cycle_yield
        self.total_capital += cycle_yield
        self.save_state()
        return cycle_yield

    def get_summary(self) -> dict:
        total_daily_yield = sum(p["projected_daily_yield"] for p in self.positions.values())
        monthly_income = total_daily_yield * 30.0
        effective_apr = (monthly_income * 12.0 / self.total_capital * 100.0) if self.total_capital > 0 else 0.0

        return {
            "vault_capital_usdt": round(self.total_capital, 2),
            "active_positions_count": len(self.positions),
            "projected_daily_usdt": round(total_daily_yield, 2),
            "projected_monthly_usdt": round(monthly_income, 2),
            "effective_apr_pct": round(effective_apr, 2),
            "total_income_collected": round(self.total_income_collected, 2)
        }


    def auto_scan_and_rebalance(self, min_apr: Optional[float] = None) -> List[dict]:
        """
        Escanea oportunidades de funding en vivo desde Binance vía CCXT y rebalancea la bóveda.
        Si CCXT no está disponible o falla, mantiene la asignación actual.
        """
        threshold = min_apr or self.min_apr_threshold
        try:
            import ccxt
            exchange = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "future"}})
            exchange.load_markets()
            funding_rates = exchange.fetch_funding_rates()
            opportunities = []
            for symbol, data in funding_rates.items():
                if not symbol.endswith(":USDT"):
                    continue
                rate = data.get("fundingRate")
                if rate is None or rate <= 0:
                    continue
                apr = rate * 3 * 365 * 100.0
                if apr >= threshold:
                    opportunities.append({
                        "symbol": symbol,
                        "apr": round(apr, 2),
                        "funding_rate": rate
                    })
            opportunities.sort(key=lambda x: x["apr"], reverse=True)
            if opportunities:
                LOG.info(f"Escaneo en vivo exitoso: {len(opportunities)} oportunidades detectadas (Top APR: {opportunities[0]['symbol']} {opportunities[0]['apr']}%)")
                self.allocate_capital(opportunities)
            return opportunities
        except Exception as e:
            LOG.warning(f"No se pudo completar el escaneo en vivo: {e}. Usando posiciones registradas.")
            return []


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Orquestador de la Bóveda Segura Delta-Neutral")
    parser.add_argument("--scan", action="store_true", help="Escanear Binance Futures en vivo")
    parser.add_argument("--capital", type=float, default=None, help="Inyectar capital inicial si la bóveda está vacía")
    args = parser.parse_args()

    vault = DeltaNeutralVault()
    if args.capital and vault.total_capital <= 0:
        vault.deposit(args.capital)

    if args.scan:
        print("[+] Escaneando Binance Futures en busca de oportunidades Cash & Carry...")
        vault.auto_scan_and_rebalance()
    elif not vault.positions:
        # Ejemplo demostrativo si no hay posiciones configuradas
        dummy_opps = [
            {"symbol": "PEPE/USDT:USDT", "apr": 32.5, "funding_rate": 0.0296},
            {"symbol": "WIF/USDT:USDT", "apr": 24.8, "funding_rate": 0.0226},
            {"symbol": "DOGE/USDT:USDT", "apr": 16.2, "funding_rate": 0.0148},
        ]
        vault.allocate_capital(dummy_opps)

    summary = vault.get_summary()
    print("=" * 65)
    print("[ESTADO DE LA BOVEDA SEGURA DELTA-NEUTRAL] (PB-69)")
    print("=" * 65)
    print(json.dumps(summary, indent=2))
    print("=" * 65)


if __name__ == "__main__":
    main()
