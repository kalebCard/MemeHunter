"""
Módulo de Ingesta y Streaming en Tiempo Real de Mercados Cripto/Memecoins.
Conecta con Binance vía CCXT / REST público para alimentar el generador de Dollar Bars.
Sprint 4: Live Market Feed & Real-Time Alpha Ingestion Pipeline.

Provee:
- Ingesta continua de trades / velas 1m de memecoins líderes (DOGE, PEPE, SHIB, BONK, WIF).
- Compresión en tiempo real a Dollar Bars con umbrales notionals dinámicos.
- Buffer rodante en memoria con acceso thread-safe.
- Sistema pub/sub de callbacks cuando se cierra una nueva Dollar Bar.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Callable, Any
import numpy as np
import pandas as pd
import ccxt

from data_engine.dollar_bars import InformationBarsGenerator

logger = logging.getLogger("LiveMarketFeed")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class LiveMarketFeed:
    """
    Ingestor en tiempo real de mercados de memecoins conectado a Binance.
    Sintetiza Dollar Bars sobre la marcha y notifica a los suscriptores.
    """

    DEFAULT_SYMBOLS = ["DOGE/USDT", "PEPE/USDT", "SHIB/USDT"]

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        notional_threshold: float = 1_000_000.0,
        poll_interval_seconds: float = 5.0,
        max_buffer_bars: int = 300,
        use_testnet: bool = False
    ):
        self.symbols = symbols or self.DEFAULT_SYMBOLS
        self.notional_threshold = notional_threshold
        self.poll_interval = poll_interval_seconds
        self.max_buffer_bars = max_buffer_bars
        self.use_testnet = use_testnet

        # Inicializar cliente CCXT Binance (Modo público, no requiere API Keys)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 10000,
            'options': {'defaultType': 'spot'}
        })
        if self.use_testnet:
            self.exchange.set_sandbox_mode(True)

        self.bar_generator = InformationBarsGenerator(notional_threshold=self.notional_threshold)
        
        # Buffers en memoria por símbolo
        self._raw_candles: Dict[str, pd.DataFrame] = {s: pd.DataFrame() for s in self.symbols}
        self._dollar_bars: Dict[str, pd.DataFrame] = {s: pd.DataFrame() for s in self.symbols}
        
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._bar_closed_callbacks: List[Callable[[str, pd.Series], None]] = []

    def subscribe_bar_closed(self, callback: Callable[[str, pd.Series], None]):
        """Registra un callback que se ejecuta cada vez que se cierra una Dollar Bar."""
        self._bar_closed_callbacks.append(callback)

    def fetch_recent_candles(self, symbol: str, limit: int = 50) -> pd.DataFrame:
        """Descarga las últimas velas 1m desde Binance."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1m', limit=limit)
            if not ohlcv:
                return pd.DataFrame()
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.warning(f"Error descargando velas para {symbol}: {e}")
            return pd.DataFrame()

    def process_incoming_candles(self, symbol: str, new_candles_df: pd.DataFrame):
        """Integra las nuevas velas y actualiza las Dollar Bars."""
        if new_candles_df.empty:
            return

        new_bar_event: Optional[Tuple[str, pd.Series]] = None

        with self._lock:
            # Concatenar y eliminar duplicados
            if symbol not in self._raw_candles or self._raw_candles[symbol].empty:
                self._raw_candles[symbol] = new_candles_df
            else:
                combined = pd.concat([self._raw_candles[symbol], new_candles_df]).drop_duplicates(subset=['timestamp'])
                self._raw_candles[symbol] = combined.tail(self.max_buffer_bars)

            # Generar Dollar Bars
            prev_len = len(self._dollar_bars[symbol]) if symbol in self._dollar_bars else 0
            bars = self.bar_generator.generate_dollar_bars(self._raw_candles[symbol])
            
            if not bars.empty:
                # Agregar columnas de microestructura requeridas por AlphaGrammar
                if 'vwap' not in bars.columns:
                    typical = (bars['high'] + bars['low'] + bars['close']) / 3.0
                    cum_vol = bars['volume'].cumsum().replace(0, 1.0)
                    bars['vwap'] = ((typical * bars['volume']).cumsum() / cum_vol).fillna(bars['close'])
                if 'rvol' not in bars.columns:
                    vol_ma = bars['volume'].rolling(20, min_periods=1).mean().replace(0, 1.0)
                    bars['rvol'] = (bars['volume'] / vol_ma).fillna(1.0)
                if 'hl_spread' not in bars.columns:
                    bars['hl_spread'] = ((bars['high'] - bars['low']) / bars['close']).fillna(0.0)
                if 'returns' not in bars.columns:
                    bars['returns'] = bars['close'].pct_change().fillna(0.0)

                self._dollar_bars[symbol] = bars.tail(self.max_buffer_bars)
                curr_len = len(self._dollar_bars[symbol])

                # Si se cerró al menos una nueva barra, preparar evento
                if curr_len > prev_len:
                    newest_bar = bars.iloc[-1].copy()
                    logger.info(f"[{symbol}] Nueva Dollar Bar cerrada a ${newest_bar['close']:.6f} (Total: {curr_len})")
                    new_bar_event = (symbol, newest_bar)

        # Notificar a los suscriptores FUERA del lock para evitar cualquier deadlock
        if new_bar_event is not None:
            sym, bar = new_bar_event
            for cb in self._bar_closed_callbacks:
                try:
                    cb(sym, bar)
                except Exception as e:
                    logger.error(f"Error en callback de Dollar Bar: {e}")

    def get_latest_dollar_bars(self, symbol: str) -> pd.DataFrame:
        """Retorna una copia segura del buffer actual de Dollar Bars para un símbolo."""
        with self._lock:
            if symbol in self._dollar_bars and not self._dollar_bars[symbol].empty:
                return self._dollar_bars[symbol].copy()
            return pd.DataFrame()

    def _poll_loop(self):
        """Bucle en segundo plano que consulta Binance periódicamente."""
        logger.info(f"Iniciando loop de streaming en tiempo real para símbolos: {self.symbols}")
        while self._running:
            for sym in self.symbols:
                if not self._running:
                    break
                df = self.fetch_recent_candles(sym, limit=40)
                self.process_incoming_candles(sym, df)
                time.sleep(0.5)  # Respetar rate limits

            time.sleep(self.poll_interval)

    def start(self):
        """Inicia el worker de ingesta en segundo plano."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="LiveMarketFeedThread")
        self._thread.start()
        logger.info("LiveMarketFeed iniciado exitosamente.")

    def stop(self):
        """Detiene el hilo de ingesta limpiamente."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("LiveMarketFeed detenido.")
