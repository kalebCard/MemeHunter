"""
Módulo de Ingesta y Streaming en Tiempo Real de Mercados Cripto/Memecoins.
Sprint 2 (2026): High-Frequency WebSocket Streaming & Adaptive Dollar Bars.

Provee:
- Conexión nativa WebSocket de baja latencia con Binance Futures (aggTrade y depth20).
- Reconexión exponencial automática (< 3s) y heartbeat para tolerancia a fallos de red.
- Agregación incremental O(1) de Dollar Bars mediante StreamingDollarBarAggregator.
- Calibración dinámica de umbrales notionales por símbolo según régimen de liquidez.
- Respaldo secundario REST vía CCXT para entornos offline, pruebas y sincronización inicial.
- Captura de orderbook L2 en memoria para soporte de microestructura y fills realistas.
"""

import os
import sys
import time
import json
import asyncio
import logging
import threading
from typing import Dict, List, Optional, Callable, Any, Tuple
import numpy as np
import pandas as pd
import ccxt

try:
    import websockets
except ImportError:
    websockets = None

from data_engine.dollar_bars import InformationBarsGenerator, StreamingDollarBarAggregator

logger = logging.getLogger("LiveMarketFeed")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class BinanceFuturesWebSocketFeed:
    """
    Cliente WebSocket asíncrono para Binance Futures (Sprint 2: US-2.1).
    Se conecta a streams multiplexados de trades y profundidad de libro L2.
    """

    WS_BASE_URL = "wss://fstream.binance.com/stream?streams="

    def __init__(
        self,
        symbols: List[str],
        on_trade_callback: Callable[[str, float, float, int], None],
        on_depth_callback: Optional[Callable[[str, List[List[float]], List[List[float]]], None]] = None,
        use_testnet: bool = False
    ):
        self.symbols = symbols
        self.on_trade = on_trade_callback
        self.on_depth = on_depth_callback
        self.use_testnet = use_testnet

        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ws_url = self._build_stream_url()

    def _symbol_to_raw(self, symbol: str) -> str:
        return symbol.replace("/", "").lower()

    def _raw_to_symbol(self, raw_symbol: str) -> str:
        raw_upper = raw_symbol.upper()
        for sym in self.symbols:
            if sym.replace("/", "").upper() == raw_upper:
                return sym
        return raw_upper

    def _build_stream_url(self) -> str:
        streams = []
        for sym in self.symbols:
            raw = self._symbol_to_raw(sym)
            streams.append(f"{raw}@aggTrade")
            streams.append(f"{raw}@depth20@100ms")
        base = "wss://stream.binancefuture.com/stream?streams=" if self.use_testnet else self.WS_BASE_URL
        return base + "/".join(streams)

    async def _listen_loop(self):
        """Bucle asíncrono de escucha con reconexión exponencial automática."""
        if websockets is None:
            logger.warning("Librería 'websockets' no disponible; WebSocketFeed no puede iniciar.")
            return

        reconnect_delay = 1.0
        while self._running:
            try:
                logger.info(f"Conectando a Binance Futures WebSocket: {self._ws_url}")
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5
                ) as ws:
                    logger.info("🟢 WebSocket de Binance Futures conectado exitosamente.")
                    reconnect_delay = 1.0

                    while self._running:
                        try:
                            msg_str = await asyncio.wait_for(ws.recv(), timeout=25.0)
                            data = json.loads(msg_str)
                            stream = data.get("stream", "")
                            payload = data.get("data", {})

                            if "@aggTrade" in stream:
                                sym = self._raw_to_symbol(payload.get("s", ""))
                                price = float(payload.get("p", 0.0))
                                qty = float(payload.get("q", 0.0))
                                ts = int(payload.get("T", int(time.time() * 1000)))
                                self.on_trade(sym, price, qty, ts)
                            elif "@depth" in stream:
                                if self.on_depth:
                                    sym = self._raw_to_symbol(payload.get("s", ""))
                                    bids = payload.get("b", [])
                                    asks = payload.get("a", [])
                                    self.on_depth(sym, bids, asks)
                        except asyncio.TimeoutError:
                            # Ping-pong de verificación
                            try:
                                pong_waiter = await ws.ping()
                                await asyncio.wait_for(pong_waiter, timeout=5.0)
                            except Exception:
                                logger.warning("Fallo en ping-pong de WebSocket; reconectando...")
                                break

            except Exception as e:
                if self._running:
                    logger.warning(f"Desconexión de WebSocket Binance ({e}). Reintento en {reconnect_delay:.1f}s...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 1.5, 5.0)

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._listen_loop())
        finally:
            self._loop.close()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True, name="BinanceFuturesWSThread")
        self._thread.start()
        logger.info("BinanceFuturesWebSocketFeed worker lanzado.")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("BinanceFuturesWebSocketFeed detenido.")


class LiveMarketFeed:
    """
    Ingestor en tiempo real de mercados de memecoins conectado a Binance.
    Integra WebSocket de baja latencia con respaldo REST y síntesis incremental O(1) de Dollar Bars.
    """

    DEFAULT_SYMBOLS = ["DOGE/USDT", "PEPE/USDT", "SHIB/USDT"]

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        notional_threshold: float = 1_000_000.0,
        symbol_thresholds: Optional[Dict[str, float]] = None,
        poll_interval_seconds: float = 5.0,
        max_buffer_bars: int = 300,
        use_websocket: bool = False,
        use_testnet: bool = False
    ):
        self.symbols = symbols or self.DEFAULT_SYMBOLS
        self.notional_threshold = float(notional_threshold)
        self.symbol_thresholds = symbol_thresholds or {}
        self.poll_interval = poll_interval_seconds
        self.max_buffer_bars = max_buffer_bars
        self.use_websocket = use_websocket
        self.use_testnet = use_testnet

        # Inicializar generador clásico y agregador incremental O(1)
        self.bar_generator = InformationBarsGenerator(
            notional_threshold=self.notional_threshold,
            symbol_thresholds=self.symbol_thresholds
        )
        self.aggregator = StreamingDollarBarAggregator(
            default_threshold=self.notional_threshold,
            symbol_thresholds=self.symbol_thresholds
        )

        # Cliente REST CCXT para respaldo
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 10000,
            'options': {'defaultType': 'spot'}
        })
        if self.use_testnet:
            self.exchange.set_sandbox_mode(True)

        # Buffers en memoria por símbolo
        self._raw_candles: Dict[str, pd.DataFrame] = {s: pd.DataFrame() for s in self.symbols}
        self._dollar_bars: Dict[str, pd.DataFrame] = {s: pd.DataFrame() for s in self.symbols}
        self._orderbooks: Dict[str, Dict[str, Any]] = {s: {"bids": [], "asks": []} for s in self.symbols}

        self._lock = threading.RLock()
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._ws_feed: Optional[BinanceFuturesWebSocketFeed] = None
        self._bar_closed_callbacks: List[Callable[[str, pd.Series], None]] = []

    def subscribe_bar_closed(self, callback: Callable[[str, pd.Series], None]):
        """Registra un callback que se ejecuta cada vez que se cierra una Dollar Bar."""
        self._bar_closed_callbacks.append(callback)

    def set_symbol_threshold(self, symbol: str, threshold: float):
        """Calibra dinámicamente el umbral para un símbolo."""
        self.bar_generator.set_threshold_for_symbol(symbol, threshold)
        self.aggregator.set_threshold(symbol, threshold)

    def calibrate_from_history(self, symbol: str, historical_df: pd.DataFrame, target_bars_per_day: float = 50.0) -> float:
        """Calibra el umbral de un símbolo en función de su volumen histórico real."""
        calibrated = self.bar_generator.calibrate_threshold_from_history(historical_df, target_bars_per_day)
        self.set_symbol_threshold(symbol, calibrated)
        logger.info(f"[{symbol}] Umbral de Dollar Bar calibrado dinámicamente a ${calibrated:,.2f} USD ({target_bars_per_day} barras/día)")
        return calibrated

    def _on_ws_trade(self, symbol: str, price: float, qty: float, timestamp_ms: int):
        """Callback invocado por el feed WebSocket al recibir un trade tick-level (Sprint 2: US-2.1/US-2.3)."""
        dt_ts = pd.to_datetime(timestamp_ms, unit='ms')
        closed_bar_dict = self.aggregator.add_tick(symbol, price, qty, dt_ts)

        if closed_bar_dict is not None:
            self._handle_closed_bar(symbol, closed_bar_dict)

    def _on_ws_depth(self, symbol: str, bids: List[List[float]], asks: List[List[float]]):
        """Actualiza el orderbook L2 en memoria."""
        with self._lock:
            self._orderbooks[symbol] = {
                "bids": [[float(p), float(q)] for p, q in bids],
                "asks": [[float(p), float(q)] for p, q in asks],
                "updated_at": time.time()
            }

    def _handle_closed_bar(self, symbol: str, bar_dict: Dict[str, Any]):
        """Agrega una barra cerrada al buffer y despacha callbacks fuera del lock."""
        bar_series: Optional[pd.Series] = None
        with self._lock:
            new_df = pd.DataFrame([bar_dict])
            if symbol not in self._dollar_bars or self._dollar_bars[symbol].empty:
                self._dollar_bars[symbol] = new_df
            else:
                self._dollar_bars[symbol] = pd.concat([self._dollar_bars[symbol], new_df], ignore_index=True)

            bars = self._dollar_bars[symbol]
            # Calcular features de microestructura
            if len(bars) > 0:
                if 'returns' not in bars.columns or bars['returns'].isna().any():
                    bars['returns'] = bars['close'].pct_change().fillna(0.0)
                if 'rvol' not in bars.columns or bars['rvol'].isna().any():
                    vol_ma = bars['volume'].rolling(20, min_periods=1).mean().replace(0, 1.0)
                    bars['rvol'] = (bars['volume'] / vol_ma).fillna(1.0)
                if 'hl_spread' not in bars.columns or bars['hl_spread'].isna().any():
                    bars['hl_spread'] = ((bars['high'] - bars['low']) / bars['close']).fillna(0.0)

                self._dollar_bars[symbol] = bars.tail(self.max_buffer_bars)
                bar_series = self._dollar_bars[symbol].iloc[-1].copy()

        if bar_series is not None:
            logger.info(f"[{symbol}] Nueva Dollar Bar O(1) cerrada a ${bar_series['close']:.6f} (Vol: {bar_series['volume']:,.0f})")
            for cb in self._bar_closed_callbacks:
                try:
                    cb(symbol, bar_series)
                except Exception as e:
                    logger.error(f"Error en callback de Dollar Bar: {e}")

    def get_latest_orderbook(self, symbol: str) -> Dict[str, Any]:
        """Retorna el estado actual del libro L2 para un símbolo."""
        with self._lock:
            return self._orderbooks.get(symbol, {"bids": [], "asks": []})

    def fetch_recent_candles(self, symbol: str, limit: int = 50) -> pd.DataFrame:
        """Descarga las últimas velas 1m desde Binance vía REST."""
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
        """Integra velas y actualiza Dollar Bars de forma incremental."""
        if new_candles_df.empty:
            return

        new_bar_event: Optional[Tuple[str, pd.Series]] = None

        with self._lock:
            if symbol not in self._raw_candles or self._raw_candles[symbol].empty:
                self._raw_candles[symbol] = new_candles_df
            else:
                combined = pd.concat([self._raw_candles[symbol], new_candles_df]).drop_duplicates(subset=['timestamp'])
                self._raw_candles[symbol] = combined.tail(self.max_buffer_bars)

            thresh = self.bar_generator.get_threshold_for_symbol(symbol)
            prev_len = len(self._dollar_bars[symbol]) if symbol in self._dollar_bars else 0
            bars = self.bar_generator.generate_dollar_bars(self._raw_candles[symbol], threshold=thresh, in_streaming=True)

            if not bars.empty:
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

                if curr_len > prev_len:
                    newest_bar = bars.iloc[-1].copy()
                    logger.info(f"[{symbol}] Nueva Dollar Bar cerrada a ${newest_bar['close']:.6f} (Total: {curr_len})")
                    new_bar_event = (symbol, newest_bar)

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
        """Bucle en segundo plano que consulta Binance REST periódicamente."""
        logger.info(f"Iniciando loop de sondeo periódico para símbolos: {self.symbols}")
        while self._running:
            for sym in self.symbols:
                if not self._running:
                    break
                df = self.fetch_recent_candles(sym, limit=40)
                self.process_incoming_candles(sym, df)
                time.sleep(0.5)

            time.sleep(self.poll_interval)

    def start(self):
        """Inicia el worker de ingesta (WebSocket primario o Sondeo REST de respaldo)."""
        if self._running:
            return
        self._running = True

        if self.use_websocket and websockets is not None:
            self._ws_feed = BinanceFuturesWebSocketFeed(
                symbols=self.symbols,
                on_trade_callback=self._on_ws_trade,
                on_depth_callback=self._on_ws_depth,
                use_testnet=self.use_testnet
            )
            self._ws_feed.start()
            logger.info("LiveMarketFeed iniciado en MODO WEBSOCKET nativo de baja latencia.")
        else:
            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True, name="LiveMarketFeedThread")
            self._poll_thread.start()
            logger.info("LiveMarketFeed iniciado en MODO SONDEO REST de respaldo.")

    def stop(self):
        """Detiene limpiamente el feed y todos los trabajadores."""
        self._running = False
        if self._ws_feed:
            self._ws_feed.stop()
            self._ws_feed = None
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=3.0)
        logger.info("LiveMarketFeed detenido.")
