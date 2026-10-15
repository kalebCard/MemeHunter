#!/usr/bin/env python3
"""
PB-02 - Descarga de histórico de klines Spot desde data.binance.vision.

Por qué existe:
    La API de Binance (y `freqtrade download-data`) solo sirve pares listados
    actualmente. data.binance.vision conserva también los pares deslistados,
    requisito para construir un universo sin sesgo de supervivencia (DAS §3.2).

Qué produce (rutas relativas al datadir, por defecto /freqtrade/user_data/data):
    binance_vision/symbols_spot.json                 -> catálogo de símbolos
    binance_vision/klines/<interval>/<SYMBOL>.feather -> klines completas (con quote_volume, trades...)
    binance_vision/manifest/<interval>/<SYMBOL>.json  -> sha256 de cada mes (reproducibilidad, DAS §2)
    binance/<BASE>_<QUOTE>-<interval>.feather         -> formato OHLCV nativo de Freqtrade

Diseñado para ejecutarse dentro del contenedor de Freqtrade:
    docker compose run --rm --entrypoint python freqtrade scripts/binance_vision.py --help
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable
try:
    import defusedxml.ElementTree as DefusedET
    SAFE_XML_PARSE = DefusedET.fromstring
except ImportError:
    from xml.etree import ElementTree as StdET
    def _safe_fromstring(xml_bytes):
        parser = StdET.XMLParser()
        # En Python 3.8+, el parser de ElementTree ya restringe entidades externas por defecto
        return StdET.fromstring(xml_bytes, parser=parser)
    SAFE_XML_PARSE = _safe_fromstring

import pandas as pd
import requests

LOG = logging.getLogger("binance_vision")

S3_LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DOWNLOAD_URL = "https://data.binance.vision"
KLINES_PREFIX = "data/spot/monthly/klines/"
S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

DEFAULT_DATADIR = Path("/freqtrade/user_data/data")
SUPPORTED_INTERVALS = ("1m", "5m", "15m", "1h", "4h", "1d")
INTERVAL_DELTA = {
    "1m": pd.Timedelta(minutes=1), "5m": pd.Timedelta(minutes=5), "15m": pd.Timedelta(minutes=15),
    "1h": pd.Timedelta(hours=1), "4h": pd.Timedelta(hours=4), "1d": pd.Timedelta(days=1),
}

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]
FULL_COLUMNS = [
    "date", "open", "high", "low", "close", "volume",
    "quote_volume", "trades", "taker_buy_base", "taker_buy_quote",
]
OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]

# Umbral para distinguir milisegundos de microsegundos.
# 1e14 ms = año 5138; 1e14 us = 1973. Binance cambió a microsegundos en 2025.
_US_THRESHOLD = 10**14


# --------------------------------------------------------------------------- #
# Utilidades puras (testeables sin red)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Month:
    year: int
    month: int

    @classmethod
    def parse(cls, text: str) -> "Month":
        m = re.fullmatch(r"(\d{4})-(\d{2})", text.strip())
        if not m or not 1 <= int(m.group(2)) <= 12:
            raise ValueError(f"Mes inválido '{text}', formato esperado YYYY-MM")
        return cls(int(m.group(1)), int(m.group(2)))

    @classmethod
    def last_complete(cls, today: date | None = None) -> "Month":
        today = today or datetime.now(timezone.utc).date()
        return cls(today.year - 1, 12) if today.month == 1 else cls(today.year, today.month - 1)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    def __lt__(self, other: "Month") -> bool:
        return (self.year, self.month) < (other.year, other.month)

    def __le__(self, other: "Month") -> bool:
        return (self.year, self.month) <= (other.year, other.month)


def split_symbol(symbol: str, quotes: Iterable[str]) -> tuple[str, str] | None:
    """'BTCUSDT' -> ('BTC', 'USDT'). Prueba las quotes más largas primero."""
    for quote in sorted(quotes, key=len, reverse=True):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol[: -len(quote)], quote
    return None


def to_freqtrade_pair(symbol: str, quotes: Iterable[str]) -> str | None:
    parts = split_symbol(symbol, quotes)
    return f"{parts[0]}/{parts[1]}" if parts else None


def parse_month_from_key(key: str) -> Month | None:
    m = re.search(r"-(\d{4})-(\d{2})\.zip$", key)
    return Month(int(m.group(1)), int(m.group(2))) if m else None


def parse_checksum(text: str) -> str:
    """Formato: '<sha256>  <filename>'."""
    digest = text.strip().split()[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError(f"CHECKSUM inválido: {text[:80]!r}")
    return digest


def parse_kline_csv(raw: bytes) -> pd.DataFrame:
    """Convierte el CSV de Binance en un DataFrame con FULL_COLUMNS.

    - Tolera cabecera opcional.
    - Normaliza timestamps en ms o us a datetime UTC.
    """
    df = pd.read_csv(io.BytesIO(raw), header=None, names=KLINE_COLUMNS, dtype=str)
    if df.empty:
        return pd.DataFrame(columns=FULL_COLUMNS)
    # Cabecera opcional: primera celda no numérica.
    if not str(df.iloc[0, 0]).strip().isdigit():
        df = df.iloc[1:]
    open_time = pd.to_numeric(df["open_time"], errors="raise").astype("int64")
    unit = "us" if int(open_time.iloc[0]) >= _US_THRESHOLD else "ms"
    out = pd.DataFrame({"date": pd.to_datetime(open_time, unit=unit, utc=True)})
    for col in FULL_COLUMNS[1:]:
        out[col] = pd.to_numeric(df[col], errors="raise").astype("float64").to_numpy()
    out["trades"] = out["trades"].astype("int64")
    return out.reset_index(drop=True)


def find_gaps(df: pd.DataFrame, interval: str, min_missing: int = 3) -> list[dict]:
    """Huecos con al menos `min_missing` velas ausentes.

    Un hueco largo suele indicar deslistado + relistado o reutilización del
    ticker (ej. LUNAUSDT: Terra clásica -> LUNA 2.0 en 2022). Uniendo ambos
    tramos, un backtest vería un salto de precio ficticio.
    """
    if len(df) < 2:
        return []
    step = INTERVAL_DELTA[interval]
    diffs = df["date"].diff()
    out = []
    for idx in df.index[diffs > step * (min_missing + 1)]:
        before, after = df.loc[idx - 1], df.loc[idx]
        out.append({
            "from": before["date"], "to": after["date"],
            "missing": int((after["date"] - before["date"]) / step) - 1,
            "price_ratio": float(after["open"] / before["close"]) if before["close"] else float("inf"),
        })
    return out


def merge_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame(columns=FULL_COLUMNS)
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="date", keep="last").sort_values("date")
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Red
# --------------------------------------------------------------------------- #
class Http:
    def __init__(self, retries: int = 4, timeout: int = 60):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "meme_hunter/0.1 (+freqtrade research)"
        self.retries = retries
        self.timeout = timeout

    def get(self, url: str, params: dict | None = None) -> requests.Response:
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 404:
                    resp.raise_for_status()
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
                resp.raise_for_status()
                return resp
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    raise
                last_exc = exc
            except requests.RequestException as exc:
                last_exc = exc
            wait = 2 ** attempt
            LOG.warning("Fallo %s (%s/%s): %s. Reintento en %ss", url, attempt, self.retries, last_exc, wait)
            time.sleep(wait)
        raise RuntimeError(f"No se pudo descargar {url}") from last_exc

    def list_s3(self, prefix: str, delimiter: str | None = None) -> tuple[list[str], list[str]]:
        """Devuelve (keys, common_prefixes) paginando con 'marker'."""
        keys: list[str] = []
        prefixes: list[str] = []
        marker = ""
        while True:
            params = {"prefix": prefix, "marker": marker}
            if delimiter:
                params["delimiter"] = delimiter
            root = SAFE_XML_PARSE(self.get(S3_LIST_URL, params=params).content)
            keys += [e.text for e in root.findall("s3:Contents/s3:Key", S3_NS) if e.text]
            prefixes += [e.text for e in root.findall("s3:CommonPrefixes/s3:Prefix", S3_NS) if e.text]
            if root.findtext("s3:IsTruncated", default="false", namespaces=S3_NS) != "true":
                break
            marker = root.findtext("s3:NextMarker", default="", namespaces=S3_NS) or (keys or prefixes)[-1]
        return keys, prefixes


# --------------------------------------------------------------------------- #
# Almacenamiento
# --------------------------------------------------------------------------- #
class Store:
    def __init__(self, datadir: Path):
        self.datadir = datadir
        self.root = datadir / "binance_vision"

    def symbols_file(self) -> Path:
        return self.root / "symbols_spot.json"

    def full_file(self, interval: str, symbol: str) -> Path:
        return self.root / "klines" / interval / f"{symbol}.feather"

    def manifest_file(self, interval: str, symbol: str) -> Path:
        return self.root / "manifest" / interval / f"{symbol}.json"

    def load_manifest(self, interval: str, symbol: str) -> dict[str, str]:
        path = self.manifest_file(interval, symbol)
        return json.loads(path.read_text()) if path.exists() else {}

    def save_manifest(self, interval: str, symbol: str, manifest: dict[str, str]) -> None:
        path = self.manifest_file(interval, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(sorted(manifest.items())), indent=1))

    def load_full(self, interval: str, symbol: str) -> pd.DataFrame | None:
        path = self.full_file(interval, symbol)
        if not path.exists():
            return None
        try:
            df = pd.read_feather(path)
            df["date"] = pd.to_datetime(df["date"], utc=True)
            return df
        except Exception as exc:
            LOG.warning("No se pudo leer %s (%s). Reconstruyendo...", path, exc)
            return None

    def save_full(self, interval: str, symbol: str, df: pd.DataFrame) -> None:
        path = self.full_file(interval, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.reset_index(drop=True).to_feather(path, compression="lz4")

    def export_freqtrade(self, pair: str, interval: str, df: pd.DataFrame) -> Path:
        """Escribe en el formato nativo de Freqtrade usando su propio DataHandler."""
        from freqtrade.data.history import get_datahandler
        from freqtrade.enums import CandleType

        handler = get_datahandler(self.datadir / "binance", data_format="feather")
        handler.ohlcv_store(pair, interval, df[OHLCV_COLUMNS].copy(), CandleType.SPOT)
        return self.datadir / "binance" / f"{pair.replace('/', '_')}-{interval}.feather"


# --------------------------------------------------------------------------- #
# Comandos
# --------------------------------------------------------------------------- #
def cmd_symbols(args: argparse.Namespace, http: Http, store: Store) -> list[str]:
    LOG.info("Listando símbolos Spot en data.binance.vision ...")
    _, prefixes = http.list_s3(KLINES_PREFIX, delimiter="/")
    all_symbols = sorted(p[len(KLINES_PREFIX):].strip("/") for p in prefixes)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(all_symbols),
        "symbols": all_symbols,
    }
    store.symbols_file().parent.mkdir(parents=True, exist_ok=True)
    store.symbols_file().write_text(json.dumps(payload, indent=1))
    filtered = [s for s in all_symbols if split_symbol(s, args.quote)]
    LOG.info("Total: %d símbolos | con quote %s: %d", len(all_symbols), "/".join(args.quote), len(filtered))
    LOG.info("Catálogo guardado en %s", store.symbols_file())
    return filtered


def _resolve_symbols(args: argparse.Namespace, http: Http, store: Store) -> list[str]:
    if args.symbols:
        return [s.upper().replace("/", "") for s in args.symbols]
    if not store.symbols_file().exists() or args.refresh_symbols:
        return cmd_symbols(args, http, store)
    data = json.loads(store.symbols_file().read_text())
    return [s for s in data["symbols"] if split_symbol(s, args.quote)]


def _download_month(http: Http, key: str) -> tuple[str, pd.DataFrame]:
    """Descarga un zip mensual, verifica sha256 y lo parsea."""
    expected = parse_checksum(http.get(f"{DOWNLOAD_URL}/{key}.CHECKSUM").text)
    blob = http.get(f"{DOWNLOAD_URL}/{key}").content
    actual = hashlib.sha256(blob).hexdigest()
    if actual != expected:
        raise ValueError(f"Checksum no coincide para {key}: {actual} != {expected}")
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"{key}: se esperaba 1 CSV, hay {csv_names}")
        df = parse_kline_csv(zf.read(csv_names[0]))
    return actual, df


def sync_symbol(
    symbol: str, interval: str, start: Month, end: Month,
    http: Http, store: Store, pool: ThreadPoolExecutor, args: argparse.Namespace,
) -> str:
    keys, _ = http.list_s3(f"{KLINES_PREFIX}{symbol}/{interval}/")
    available = {
        m: k for k in keys
        if k.endswith(".zip") and (m := parse_month_from_key(k)) and start <= m <= end
    }
    if not available:
        return "sin datos en rango"

    manifest = {} if args.force else store.load_manifest(interval, symbol)
    pending = {m: k for m, k in available.items() if str(m) not in manifest}
    existing = None if args.force else store.load_full(interval, symbol)

    if not pending and existing is not None:
        status = "al día"
        df = existing
    else:
        futures = {pool.submit(_download_month, http, k): m for m, k in pending.items()}
        frames = [existing] if existing is not None else []
        errors = []
        for fut in as_completed(futures):
            month = futures[fut]
            try:
                digest, frame = fut.result()
                frames.append(frame)
                manifest[str(month)] = digest
            except Exception as exc:  # noqa: BLE001 - se registra y se continúa
                errors.append(f"{month}: {exc}")
        for err in errors:
            LOG.error("%s %s %s", symbol, interval, err)
        df = merge_frames(frames)
        if df.empty:
            return "error"
        store.save_full(interval, symbol, df)
        store.save_manifest(interval, symbol, manifest)
        status = f"+{len(pending) - len(errors)} meses" + (f", {len(errors)} errores" if errors else "")

    if not args.no_freqtrade:
        pair = to_freqtrade_pair(symbol, args.quote)
        if pair:
            store.export_freqtrade(pair, interval, df)
    for gap in find_gaps(df, interval):
        LOG.warning(
            "%s %s HUECO %s -> %s (%d velas, ratio precio x%.4g). Revisar en PB-04.",
            symbol, interval, f"{gap['from']:%Y-%m-%d %H:%M}", f"{gap['to']:%Y-%m-%d %H:%M}",
            gap["missing"], gap["price_ratio"],
        )
    first, last = df["date"].iloc[0], df["date"].iloc[-1]
    return f"{status} | {len(df):,} velas | {first:%Y-%m-%d} -> {last:%Y-%m-%d}"


def cmd_download(args: argparse.Namespace, http: Http, store: Store) -> int:
    start = Month.parse(args.start)
    end = Month.parse(args.end) if args.end else Month.last_complete()
    if end < start:
        LOG.error("--end (%s) es anterior a --start (%s)", end, start)
        return 2
    symbols = _resolve_symbols(args, http, store)
    if args.limit:
        symbols = symbols[: args.limit]
    LOG.info("Descargando %d símbolos | intervalos %s | %s -> %s", len(symbols), args.interval, start, end)

    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for interval in args.interval:
            for i, symbol in enumerate(symbols, 1):
                try:
                    result = sync_symbol(symbol, interval, start, end, http, store, pool, args)
                except Exception as exc:  # noqa: BLE001
                    failures += 1
                    result = f"ERROR: {exc}"
                LOG.info("[%s %d/%d] %-14s %s", interval, i, len(symbols), symbol, result)
    LOG.info("Terminado. Fallos: %d", failures)
    return 1 if failures else 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datadir", type=Path, default=DEFAULT_DATADIR)
    parser.add_argument("--quote", nargs="+", default=["USDT"], help="Quotes a considerar (default: USDT)")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("symbols", help="Lista y cachea todos los símbolos Spot (incluye deslistados)")

    dl = sub.add_parser("download", help="Descarga y convierte klines mensuales")
    sel = dl.add_mutually_exclusive_group(required=True)
    sel.add_argument("--symbols", nargs="+", help="Ej: BTCUSDT ETHUSDT (o BTC/USDT)")
    sel.add_argument("--all-symbols", action="store_true", help="Todos los símbolos con la quote indicada")
    dl.add_argument("--interval", nargs="+", default=["1d"], choices=SUPPORTED_INTERVALS)
    dl.add_argument("--start", default="2020-01", help="YYYY-MM (default 2020-01)")
    dl.add_argument("--end", help="YYYY-MM (default: último mes completo)")
    dl.add_argument("--workers", type=int, default=8)
    dl.add_argument("--limit", type=int, help="Procesar solo los primeros N símbolos (pruebas)")
    dl.add_argument("--force", action="store_true", help="Ignorar manifest y redescargar")
    dl.add_argument("--refresh-symbols", action="store_true", help="Volver a listar símbolos")
    dl.add_argument("--no-freqtrade", action="store_true", help="No exportar al formato de Freqtrade")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    args.quote = [q.upper() for q in args.quote]
    http, store = Http(), Store(args.datadir)
    if args.command == "symbols":
        cmd_symbols(args, http, store)
        return 0
    return cmd_download(args, http, store)


if __name__ == "__main__":
    sys.exit(main())
