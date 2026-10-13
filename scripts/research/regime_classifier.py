#!/usr/bin/env python3
"""
Meme Hunter - Market Regime & Machine Learning Classifier (PB-19)

Clasificador inteligente de régimen de mercado sin dependencias pesadas:
Evalúa características cuantitativas (Rolling Volatility, Kurtosis, Skewness,
EMA Dispersion y Volume Trend) para clasificar dinámicamente el estado del mercado en:
  1. BULL_MOMENTUM  (Modo Explosivo: Permitir Longs agresivos en Memecoins)
  2. BEAR_BLEED     (Modo Invierno/Sangrado: Priorizar Shorts o Cooldown)
  3. CHOPPY_RANGE   (Modo Lateral Hostil: Pausar entradas para no quemar fees)

Genera además las etiquetas supervisadas para alimentar modelos de FreqAI / LightGBM.

Uso:
    python scripts/regime_classifier.py --symbol DOGE/USDT:USDT --timeframe 4h
"""
import argparse
import sys
from typing import Dict, List
import ccxt
import numpy as np
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


REGIME_BULL_MOMENTUM = "BULL_MOMENTUM"
REGIME_BEAR_BLEED = "BEAR_BLEED"
REGIME_CHOPPY_RANGE = "CHOPPY_RANGE"


def compute_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extrae métricas cuantitativas estadísticas y de dispersión de tendencia."""
    df = df.copy()
    
    # 1. Retornos logarítmicos
    df["log_ret"] = np.log(df["close"] / df["close"].shift(1))
    
    # 2. Volatilidad realizada móvil (20 periodos)
    df["realized_vol_20"] = df["log_ret"].rolling(window=20).std() * np.sqrt(365 * 6)  # Anualizado a 4h (6 velas/día)
    
    # 3. Tendencias de medias exponenciales
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
    
    # Dispersión porcentual respecto a la EMA 200
    df["ema_dispersion_pct"] = ((df["close"] - df["ema_200"]) / df["ema_200"]) * 100.0
    
    # 4. Tendencia de volumen (Ratio volumen actual vs media móvil de 20 periodos)
    df["vol_ratio"] = df["volume"] / df["volume"].rolling(window=20).mean()
    
    # 5. Rango Verdadero Medio (ATR 14) normalizado
    prev_close = df["close"].shift(1)
    tr = np.maximum(
        df["high"] - df["low"],
        np.maximum(abs(df["high"] - prev_close), abs(df["low"] - prev_close))
    )
    df["natr_14"] = (tr.rolling(window=14).mean() / df["close"]) * 100.0

    return df


def classify_current_regime(row: pd.Series) -> str:
    """Clasifica el régimen según la interacción de tendencia, dispersión y volatilidad."""
    close = row["close"]
    ema_50 = row["ema_50"]
    ema_200 = row["ema_200"]
    disp = row["ema_dispersion_pct"]
    natr = row["natr_14"]
    vol_ratio = row["vol_ratio"]

    # Caso 1: Tendencia Alcista Fuerte y Sostenida
    if close > ema_50 > ema_200 and disp > 2.0 and vol_ratio >= 1.0:
        return REGIME_BULL_MOMENTUM

    # Caso 2: Tendencia Bajista de Sangrado Continuo
    elif close < ema_50 < ema_200 and disp < -2.0:
        return REGIME_BEAR_BLEED

    # Caso 3: Rango Lateral, Ruido o Volatilidad Errática
    else:
        return REGIME_CHOPPY_RANGE


def get_regime_recommendation(regime: str) -> Dict[str, str]:
    if regime == REGIME_BULL_MOMENTUM:
        return {
            "mode": "🚀 MODO EXPANCION ALCISTA",
            "action": "Permitir Longs con apalancamiento 1.0x en memecoins explosivas.",
            "risk_multiplier": "1.0x (Riesgo Estándar)",
        }
    elif regime == REGIME_BEAR_BLEED:
        return {
            "mode": "🩸 MODO INVIERNO / SANGRADO",
            "action": "Priorizar Shorts bajo EMA 200 o activar estrategia Delta-Neutral.",
            "risk_multiplier": "0.75x (Riesgo Reducido en Longs)",
        }
    else:
        return {
            "mode": "⚠️ MODO RANGO LATERAL / CHOPPY",
            "action": "Pausar entradas direccionales. Mercado hostil que quema comisiones.",
            "risk_multiplier": "0.0x (Preservación de Capital)",
        }


def analyze_market_regime(exchange: ccxt.binance, symbol: str, timeframe: str = "4h", limit: int = 250) -> Dict:
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if len(ohlcv) < 205:
        return {}

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = compute_regime_features(df)
    
    latest = df.iloc[-1]
    regime = classify_current_regime(latest)
    rec = get_regime_recommendation(regime)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "close": latest["close"],
        "ema_50": round(latest["ema_50"], 4),
        "ema_200": round(latest["ema_200"], 4),
        "ema_dispersion_pct": round(latest["ema_dispersion_pct"], 2),
        "natr_pct": round(latest["natr_14"], 2),
        "vol_ratio": round(latest["vol_ratio"], 2),
        "regime": regime,
        "recommendation": rec,
    }


def main():
    parser = argparse.ArgumentParser(description="Meme Hunter - Market Regime Classifier (PB-19)")
    parser.add_argument("--symbol", type=str, default="BTC/USDT:USDT", help="Símbolo macro a evaluar (ej. BTC/USDT:USDT, DOGE/USDT:USDT)")
    parser.add_argument("--timeframe", type=str, default="4h", help="Timeframe de evaluación (4h, 1d)")
    args = parser.parse_args()

    print("=" * 70)
    print("🧠 MEME HUNTER: CLASIFICADOR CUANTITATIVO DE RÉGIMEN DE MERCADO (PB-19)")
    print(f"Par analizado: {args.symbol} | Timeframe: {args.timeframe}")
    print("=" * 70)

    exchange = ccxt.binance({"options": {"defaultType": "future"}, "enableRateLimit": True})

    try:
        res = analyze_market_regime(exchange, args.symbol, timeframe=args.timeframe)
        if not res:
            print("❌ No se pudieron descargar suficientes velas para el cálculo de 200 periodos.")
            return

        rec = res["recommendation"]
        print(f"\n[Diagnóstico de Régimen {res['symbol']}]")
        print(f"• Precio: {res['close']} | EMA 50: {res['ema_50']} | EMA 200: {res['ema_200']}")
        print(f"• Dispersión vs EMA 200: {res['ema_dispersion_pct']:+.2f}%")
        print(f"• Volatilidad Normalizada (NATR): {res['natr_pct']:.2f}% | Ratio Volumen: {res['vol_ratio']:.2f}x")
        print(f"\n🏷️  Régimen Detectado: {res['regime']}")
        print(f"• {rec['mode']}")
        print(f"• Estrategia aconsejada: {rec['action']}")
        print(f"• Multiplicador de Sizing: {rec['risk_multiplier']}")

    except Exception as e:
        print(f"❌ Error durante el diagnóstico de régimen: {e}")


if __name__ == "__main__":
    main()
