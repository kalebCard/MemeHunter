#!/usr/bin/env python3
"""
scripts/triple_barrier_metalabeling.py
--------------------------------------
Módulo de Etiquetado por Triple Barrera y Meta-Etiquetado con Bet Sizing Continuo.

Implementa:
1. Método de la Triple Barrera (Triple-Barrier Method):
   - Barrera superior (Take-Profit): Múltiplo de volatilidad dinámica EWMA / ATR (+1).
   - Barrera inferior (Stop-Loss): Múltiplo de volatilidad dinámica EWMA / ATR (-1).
   - Barrera vertical (Time Expiration): Límite temporal de N periodos (0 o retorno final).
2. Meta-Etiquetado (Meta-Labeling):
   - Separa la señal primaria direccional (ej. Short por quiebre de estructura)
     de la predicción secundaria de convicción (éxito binario 1 vs fracaso 0).
3. Bet Sizing Continuo (Fórmula de López de Prado / Kelly Sigmoidal):
   - m = 2 * Z[ (p - 0.5) / sqrt(p * (1 - p)) ] - 1
   - Traduce la probabilidad pronosticada p in [0, 1] en una escala continua de apalancamiento/tamaño.

Referencia:
- López de Prado, M. (2018). Advances in Financial Machine Learning, Capítulos 3 y 10.
"""

import math
import numpy as np
import pandas as pd
import scipy.stats as ss
from typing import Dict, Any, Tuple, Optional


def get_daily_volatility(close: pd.Series, span: int = 24) -> pd.Series:
    """
    Calcula la volatilidad continua ponderada exponencialmente (EWMA)
    sobre los retornos logarítmicos de la serie.
    span=24 equivale a ~4 días en velas de 4h o 1 día en velas de 1h.
    """
    returns = np.log(close / close.shift(1))
    vol = returns.ewm(span=span).std()
    return vol


def apply_triple_barrier(
    close: pd.Series,
    events_idx: pd.Index,
    pt_sl: Tuple[float, float] = (2.0, 1.0),
    max_holding_periods: int = 18,
    volatility: Optional[pd.Series] = None
) -> pd.DataFrame:
    """
    Aplica el Método de la Triple Barrera para una lista de eventos (índices de entrada).
    
    close: Serie de precios de cierre.
    events_idx: Índices donde el modelo primario generó una señal.
    pt_sl: Tupla (multiplicador_profit_target, multiplicador_stop_loss).
    max_holding_periods: Barrera vertical (número máximo de velas antes de forzar cierre).
    volatility: Serie de volatilidad (si es None, se calcula vía EWMA).
    
    Retorna un DataFrame con:
    - entry_price
    - exit_price
    - exit_time
    - barrier_hit: 'pt' (+1), 'sl' (-1) o 'time' (0)
    - return: retorno porcentual exacto
    - target_label: 1 si trade fue ganador (hit PT), 0 en caso contrario
    """
    if volatility is None:
        volatility = get_daily_volatility(close)
        
    records = []
    close_idx = close.index
    
    for entry_time in events_idx:
        if entry_time not in close_idx:
            continue
            
        loc = close_idx.get_loc(entry_time)
        entry_price = close.iloc[loc]
        vol = volatility.iloc[loc]
        
        if np.isnan(vol) or vol <= 1e-6:
            vol = 0.02  # Fallback a 2% si volatilidad no está disponible
            
        pt_dist = pt_sl[0] * vol
        sl_dist = pt_sl[1] * vol
        
        # Para posiciones SHORT (nuestro enfoque principal de desinflación):
        # Target abajo: entry * (1 - pt_dist)
        # Stop arriba: entry * (1 + sl_dist)
        short_pt_price = entry_price * (1.0 - pt_dist)
        short_sl_price = entry_price * (1.0 + sl_dist)
        
        exit_time = entry_time
        exit_price = entry_price
        barrier_hit = 'time'
        
        end_loc = min(len(close), loc + max_holding_periods + 1)
        future_window = close.iloc[loc + 1 : end_loc]
        
        for t, price in future_window.items():
            # Condición de Stop-Loss en Short
            if price >= short_sl_price:
                exit_time = t
                exit_price = short_sl_price
                barrier_hit = 'sl'
                break
            # Condición de Take-Profit en Short
            elif price <= short_pt_price:
                exit_time = t
                exit_price = short_pt_price
                barrier_hit = 'pt'
                break
                
        if barrier_hit == 'time':
            if len(future_window) > 0:
                exit_time = future_window.index[-1]
                exit_price = future_window.iloc[-1]
            else:
                exit_price = entry_price
                
        # Retorno para posición SHORT: (entry - exit) / entry
        ret = (entry_price - exit_price) / entry_price
        label = 1 if ret > 0 else 0
        
        records.append({
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "barrier_hit": barrier_hit,
            "return": ret,
            "meta_label": label
        })
        
    return pd.DataFrame(records)


def continuous_bet_sizing(
    prob_success: float,
    min_prob_threshold: float = 0.52,
    max_leverage: float = 2.0,
    min_leverage: float = 1.0
) -> float:
    """
    Traduce la probabilidad predicha p in [0, 1] por el Meta-Modelo
    a una asignación de tamaño / apalancamiento continuo m.
    
    Fórmula de Marcos López de Prado:
    z = (p - 0.5) / sqrt(p * (1 - p))
    m = 2 * norm_cdf(z) - 1
    
    Si p <= min_prob_threshold, m = 0 (no operar / filtrar señal primaria ruidosa).
    Si p > min_prob_threshold, interpola suavemente entre min_leverage y max_leverage.
    """
    if prob_success <= min_prob_threshold:
        return 0.0
        
    p = min(0.999, max(0.001, prob_success))
    denom = math.sqrt(p * (1.0 - p))
    z = (p - 0.5) / denom
    m = 2.0 * float(ss.norm.cdf(z)) - 1.0  # m in (0, 1)
    
    # Escalar m continuo al rango [min_leverage, max_leverage]
    leverage = min_leverage + m * (max_leverage - min_leverage)
    return round(leverage, 2)


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 EJECUCIÓN DEMOSTRATIVA DE TRIPLE BARRIER & META-LABELING")
    print("=" * 70)
    
    # Crear serie de precios simulados
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=500, freq="4h")
    trend = -0.001 * np.arange(500)  # Tendencia desinflacionaria
    noise = np.random.normal(0, 0.03, 500)
    prices = pd.Series(100.0 * np.exp(np.cumsum(trend + noise)), index=dates)
    
    # Eventos de entrada ficticios cada 25 velas
    events = dates[10::25]
    
    tb_df = apply_triple_barrier(prices, events_idx=events, pt_sl=(2.0, 1.0), max_holding_periods=12)
    print(f"Total eventos etiquetados: {len(tb_df)}")
    print(f"Desglose de barreras impactadas:")
    print(tb_df["barrier_hit"].value_counts())
    print(f"\nMeta-labels: Ganadores={sum(tb_df['meta_label'] == 1)}, Perdedores={sum(tb_df['meta_label'] == 0)}")
    print(f"Retorno medio en Shorts: {tb_df['return'].mean()*100:.2f}%")
    
    # Demostración de Bet Sizing Continuo
    print("\n📐 Escala de Bet Sizing Continuo según Probabilidad del Meta-Modelo:")
    for prob in [0.45, 0.50, 0.53, 0.58, 0.65, 0.75, 0.85]:
        lev = continuous_bet_sizing(prob, min_prob_threshold=0.52, max_leverage=2.0, min_leverage=1.0)
        status = "⛔ Filtrado (0.0x)" if lev == 0.0 else f"✅ Operar con {lev:.2f}x"
        print(f"   Probabilidad p={prob:.2f} -> {status}")
