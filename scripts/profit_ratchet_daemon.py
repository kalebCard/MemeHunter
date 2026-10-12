"""
profit_ratchet_daemon.py - Daemon Centinela de Trinquete de Ganancias (PB-68).

Monitorea la equidad de Freqtrade (vía SQLite o API REST) y administra la
desconexión del riesgo:
1. Audita el capital actual: Balance realizado + PnL no realizado.
2. Si el equity alcanza el hito de ganancia (ej. +100% sobre base), ejecuta la
   cosecha (Harvesting) del porcentaje estipulado hacia la Bóveda Segura (Spot/Arbitraje).
3. Resetea la base operativa para proteger el capital cosechado.
4. Vigila el Kill-Switch al 25% de drawdown vivo desde el último pico.
"""

import sys
import time
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
LOG = logging.getLogger("ProfitRatchet")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "user_data" / "tradesv3.futures.sqlite"
STATE_FILE = ROOT / "user_data" / "ratchet_state.json"
KILL_SWITCH_FILE = ROOT / "user_data" / "KILL_SWITCH"


class ProfitRatchetDaemon:
    def __init__(
        self,
        db_path: Path = DEFAULT_DB,
        starting_capital: float = 1000.0,
        harvest_target_pct: float = 1.0,     # +100% de beneficio activa el trinquete
        harvest_ratio: float = 0.60,         # 60% a la bóveda segura, 40% reinversión
        kill_switch_dd: float = 0.25,        # 25% Drawdown corta operaciones
        dry_run: bool = True,
        state_file: Path = STATE_FILE
    ):
        self.db_path = db_path
        self.state_file = state_file
        self.base_capital = starting_capital
        self.harvest_target_pct = harvest_target_pct
        self.harvest_ratio = harvest_ratio
        self.kill_switch_dd = kill_switch_dd
        self.dry_run = dry_run

        self.peak_equity = starting_capital
        self.total_harvested = 0.0
        self.cycle_count = 0

        self.load_state()

    def load_state(self):
        if self.state_file and self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.base_capital = data.get("base_capital", self.base_capital)
                    self.peak_equity = data.get("peak_equity", self.peak_equity)
                    self.total_harvested = data.get("total_harvested", 0.0)
                    self.cycle_count = data.get("cycle_count", 0)
                    LOG.info(f"Estado restaurado: Base={self.base_capital:.2f}, Cosechado={self.total_harvested:.2f}, Ciclo={self.cycle_count}")
            except Exception as e:
                LOG.warning(f"No se pudo cargar estado previo: {e}")

    def save_state(self):
        if not self.state_file:
            return
        data = {
            "base_capital": self.base_capital,
            "peak_equity": self.peak_equity,
            "total_harvested": self.total_harvested,
            "cycle_count": self.cycle_count,
            "updated_at": datetime.utcnow().isoformat()
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_db_metrics(self):
        if not self.db_path.exists():
            return {"realized_profit": 0.0, "open_trades": 0}

        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT is_open, close_profit_abs FROM trades").fetchall()

        realized_profit = sum(r["close_profit_abs"] or 0.0 for r in rows if not r["is_open"])
        open_trades = sum(1 for r in rows if r["is_open"])
        return {"realized_profit": realized_profit, "open_trades": open_trades}

    def check_and_ratchet(self, external_unrealized_pnl: float = 0.0):
        metrics = self.get_db_metrics()
        realized = metrics["realized_profit"]
        
        current_equity = self.base_capital + realized + external_unrealized_pnl

        # 1. Actualizar pico de equidad
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        # 2. Verificar Kill-Switch (Drawdown desde el pico)
        drawdown = (self.peak_equity - current_equity) / self.peak_equity if self.peak_equity > 0 else 0.0
        if drawdown >= self.kill_switch_dd:
            LOG.error(f"🚨 KILL-SWITCH ACTIVADO: Drawdown de {drawdown*100:.2f}% >= {self.kill_switch_dd*100:.1f}%.")
            if not self.dry_run:
                KILL_SWITCH_FILE.write_text(f"TRIGGERED_{datetime.utcnow().isoformat()}")
            return {"status": "KILLED", "drawdown": drawdown, "equity": current_equity}

        # 3. Verificar Disparador de Trinquete (Harvesting)
        target_equity = self.base_capital * (1.0 + self.harvest_target_pct)
        if current_equity >= target_equity:
            profit = current_equity - self.base_capital
            amount_to_vault = profit * self.harvest_ratio
            amount_reinvest = profit * (1.0 - self.harvest_ratio)

            self.cycle_count += 1
            self.total_harvested += amount_to_vault
            self.base_capital += amount_reinvest
            self.peak_equity = self.base_capital

            LOG.info("=" * 65)
            LOG.info(f"🎉 HITO DE TRINQUETE ALCANZADO (Ciclo #{self.cycle_count})")
            LOG.info(f"Equity: {current_equity:.2f} USDT | Ganancia de Ciclo: {profit:.2f} USDT")
            LOG.info(f"-> Transferido a Boveda Segura ({self.harvest_ratio*100:.0f}%): {amount_to_vault:.2f} USDT")
            LOG.info(f"-> Reinvertido en Motor Alpha ({ (1-self.harvest_ratio)*100:.0f}%): {amount_reinvest:.2f} USDT")
            LOG.info(f"-> Total Acumulado en Boveda Segura: {self.total_harvested:.2f} USDT")
            LOG.info(f"-> Nueva Base Operativa Alpha: {self.base_capital:.2f} USDT")
            LOG.info("=" * 65)

            if not self.dry_run:
                self.execute_binance_transfer(amount_to_vault)

            self.save_state()
            return {"status": "HARVESTED", "harvested": amount_to_vault, "equity": self.base_capital}

        self.save_state()
        return {"status": "NORMAL", "equity": current_equity, "drawdown": drawdown}

    def execute_binance_transfer(self, amount: float):
        LOG.info(f"[CCXT TRANSFER] Transferir {amount:.2f} USDT de Futures a Spot...")
        # Integración con ccxt: exchange.transfer('USDT', amount, 'future', 'spot')
        pass


def main():
    parser = argparse.ArgumentParser(description="Daemon Centinela de Trinquete de Ganancias (PB-68)")
    parser.add_argument("--capital", type=float, default=1000.0, help="Capital base del motor de futuros")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Modo simulado")
    parser.add_argument("--once", action="store_true", help="Ejecutar una sola auditoría y salir")
    args = parser.parse_args()

    daemon = ProfitRatchetDaemon(starting_capital=args.capital, dry_run=args.dry_run)
    LOG.info(f"Profit Ratchet Daemon iniciado (Capital={args.capital} USDT, DryRun={args.dry_run})")

    if args.once:
        res = daemon.check_and_ratchet()
        print(json.dumps(res, indent=2))
        return

    while True:
        try:
            daemon.check_and_ratchet()
            time.sleep(30)
        except KeyboardInterrupt:
            LOG.info("Detención solicitada.")
            break
        except Exception as e:
            LOG.error(f"Error en bucle del daemon: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
