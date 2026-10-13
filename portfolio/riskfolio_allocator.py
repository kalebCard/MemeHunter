"""
portfolio/riskfolio_allocator.py
--------------------------------
Asignador Institucional de Portafolio con Riskfolio-Lib (Sprint 34: PB-117 & PB-118).

Implementa:
1. Optimización Jerárquica de Riesgo con colas pesadas:
   - HERC (Hierarchical Equal Risk Contribution) con CVaR al 99% (Expected Shortfall).
   - Medidas de riesgo asimétricas para memecoins: CDaR (Conditional Drawdown at Risk) y VaR.
2. Zona Muerta de Rotación (Turnover Deadband del 15%):
   - Evita rebalanceos marginales que consuman capital en comisiones innecesarias en Freqtrade.
3. Evaluación de Riesgo de Cola y Contribución Marginal de CVaR (PB-118):
   - Audita si la adición de una estrategia eleva el riesgo de liquidación del portafolio.
"""

from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger("RiskfolioAllocator")

try:
    import riskfolio as rp
    RISKFOLIO_AVAILABLE = True
except Exception:
    rp = None
    RISKFOLIO_AVAILABLE = False


class RiskfolioPortfolioAllocator:
    """
    Asignador avanzado de capital para el portafolio de Meme Hunter utilizando Riskfolio-Lib.
    Optimiza la asignación frente a distribuciones no gaussianas y colas pesadas de memecoins.
    """

    def __init__(
        self,
        model: str = "HERC",            # 'HERC', 'HRP', 'NCO'
        rm: str = "CVaR",               # 'CVaR', 'CDaR', 'MV', 'MDD'
        rf: float = 0.0,                # Tasa libre de riesgo
        alpha: float = 0.01,            # 99% nivel de confianza (1% cola izquierda)
        turnover_deadband: float = 0.15, # 15% zona muerta para no sobre-rotar
        use_riskfolio_if_available: bool = True
    ):
        self.model = model.upper()
        self.rm = rm
        self.rf = float(rf)
        self.alpha = float(alpha)
        self.deadband = float(turnover_deadband)
        self.use_riskfolio = use_riskfolio_if_available and RISKFOLIO_AVAILABLE

        if self.use_riskfolio:
            logger.info(f"RiskfolioPortfolioAllocator: Motor Riskfolio ACTIVO ({self.model} / {self.rm} alpha={self.alpha}).")
        else:
            logger.info("RiskfolioPortfolioAllocator: Motor CVaR-HERC analítico nativo ACTIVO.")

    def allocate_weights(
        self,
        returns_df: pd.DataFrame,
        current_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Calcula los pesos óptimos del portafolio.
        Si la desviación respecto a `current_weights` no supera el deadband, retiene los pesos previos.
        """
        clean_df = returns_df.dropna(how="all").fillna(0.0)
        assets = list(clean_df.columns)
        n = len(assets)

        if n == 0:
            return {}
        if n == 1:
            return {assets[0]: 1.0}

        # 1. Resolver pesos brutos con Riskfolio o Fallback
        if self.use_riskfolio and rp is not None:
            try:
                raw_weights = self._allocate_with_riskfolio(clean_df)
            except Exception as e:
                logger.warning(f"Aviso en optimización Riskfolio ({e}). Utilizando motor CVaR-HERC nativo.")
                raw_weights = self._allocate_with_native_herc(clean_df)
        else:
            raw_weights = self._allocate_with_native_herc(clean_df)

        # 2. Aplicar Zona Muerta de Rotación (Turnover Deadband)
        if current_weights:
            final_weights = self._apply_turnover_deadband(raw_weights, current_weights)
        else:
            final_weights = raw_weights

        # Asegurar suma 1.0 exacta
        total_w = sum(final_weights.values())
        if total_w > 0:
            final_weights = {k: round(v / total_w, 6) for k, v in final_weights.items()}

        return final_weights

    def _allocate_with_riskfolio(self, clean_df: pd.DataFrame) -> Dict[str, float]:
        """Asignación utilizando HCPortfolio de Riskfolio-Lib."""
        port = rp.HCPortfolio(returns=clean_df)
        w = port.optimization(
            model=self.model,
            correlation="pearson",
            rm=self.rm,
            rf=self.rf,
            linkage="ward",
            max_k=10,
            leaf_order=True
        )

        if w is None or w.empty:
            raise ValueError("Riskfolio retornó pesos vacíos.")

        weights_dict = {}
        for col in clean_df.columns:
            if col in w.index:
                val = float(w.loc[col].iloc[0]) if hasattr(w.loc[col], "iloc") else float(w.loc[col])
                weights_dict[col] = max(0.0, val)
            else:
                weights_dict[col] = 0.0

        return weights_dict

    def _allocate_with_native_herc(self, clean_df: pd.DataFrame) -> Dict[str, float]:
        """
        Asignación analítica HERC con ponderación de colas pesadas (CVaR).
        Calcula el CVaR al 99% para cada activo y realiza división recursiva jerárquica.
        """
        from scipy.cluster.hierarchy import linkage, to_tree
        from scipy.spatial.distance import squareform

        assets = list(clean_df.columns)
        n = len(assets)

        corr = clean_df.corr().to_numpy()
        corr = np.nan_to_num(corr, copy=True, nan=0.0)
        np.fill_diagonal(corr, 1.0)

        # Distancia ultramétrica de correlación: d = sqrt(0.5 * (1 - rho))
        dist_mat = np.sqrt(0.5 * np.maximum(0.0, 1.0 - corr))
        np.fill_diagonal(dist_mat, 0.0)
        condensed_dist = squareform(dist_mat, checks=False)

        link = linkage(condensed_dist, method="ward")
        root = to_tree(link, rd=False)

        def _get_leaves(node):
            if node.is_leaf():
                return [node.id]
            return _get_leaves(node.left) + _get_leaves(node.right)

        sorted_indices = _get_leaves(root)

        # Calcular CVaR empírico al 99% para cada activo
        cvars = np.zeros(n)
        for i, col in enumerate(assets):
            series = clean_df[col].to_numpy()
            q_alpha = np.quantile(series, self.alpha)
            tail = series[series <= q_alpha]
            if len(tail) > 0:
                cvars[i] = max(1e-4, -float(np.mean(tail)))
            else:
                cvars[i] = max(1e-4, float(np.std(series) * 2.33))

        # Ponderación inversa recursiva del CVaR
        weights = pd.Series(1.0, index=sorted_indices)
        clusters = [sorted_indices]

        while len(clusters) > 0:
            next_clusters = []
            for cl in clusters:
                if len(cl) > 1:
                    mid = len(cl) // 2
                    c1 = cl[:mid]
                    c2 = cl[mid:]

                    # Riesgo agregado de cada sub-clúster
                    cvar1 = float(np.mean(cvars[c1]))
                    cvar2 = float(np.mean(cvars[c2]))

                    # Reparto inversamente proporcional al riesgo de cola
                    alpha_factor = cvar2 / (cvar1 + cvar2 + 1e-12)
                    alpha_factor = np.clip(alpha_factor, 0.05, 0.95)

                    weights[c1] *= alpha_factor
                    weights[c2] *= (1.0 - alpha_factor)

                    if len(c1) > 1:
                        next_clusters.append(c1)
                    if len(c2) > 1:
                        next_clusters.append(c2)
            clusters = next_clusters

        total_w = float(weights.sum())
        weights = weights / (total_w if total_w > 0 else 1.0)

        out_weights = {assets[i]: float(weights[i]) for i in sorted_indices}
        return out_weights

    def _apply_turnover_deadband(
        self,
        new_weights: Dict[str, float],
        current_weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Aplica la zona muerta de rotación: retiene pesos si el cambio es marginal (< deadband)."""
        all_keys = set(new_weights.keys()).union(set(current_weights.keys()))
        total_turnover = 0.0

        for k in all_keys:
            w_new = new_weights.get(k, 0.0)
            w_curr = current_weights.get(k, 0.0)
            total_turnover += abs(w_new - w_curr)

        # Si el turnover total del portafolio es inferior al umbral, no se rebalancea
        if total_turnover < self.deadband:
            logger.info(
                f"Turnover {total_turnover:.4f} < deadband {self.deadband:.4f}. "
                "Reteniendo pesos activos para evitar comisiones."
            )
            return {k: current_weights.get(k, 0.0) for k in new_weights.keys()}

        return new_weights

    def compute_portfolio_tail_risk(
        self,
        returns_df: pd.DataFrame,
        weights: Dict[str, float],
        alpha: float = 0.01
    ) -> Dict[str, float]:
        """
        Calcula las métricas formales de riesgo de cola del portafolio:
        - VaR paramétrico y empírico al 99%.
        - CVaR (Expected Shortfall) al 99%.
        - Maximum Drawdown (MDD).
        - CDaR (Conditional Drawdown at Risk).
        """
        clean_df = returns_df.dropna(how="all").fillna(0.0)
        w_vec = np.array([weights.get(col, 0.0) for col in clean_df.columns])

        # Serie de retornos del portafolio
        port_ret = clean_df.to_numpy() @ w_vec

        if len(port_ret) == 0:
            return {"var_99": 0.0, "cvar_99": 0.0, "max_drawdown": 0.0, "cdar_99": 0.0}

        # 1. VaR y CVaR
        q_alpha = np.quantile(port_ret, alpha)
        var_val = float(-q_alpha)

        tail_losses = port_ret[port_ret <= q_alpha]
        cvar_val = float(-np.mean(tail_losses)) if len(tail_losses) > 0 else var_val

        # 2. Maximum Drawdown y CDaR
        cum_ret = np.cumsum(port_ret)
        cum_peak = np.maximum.accumulate(cum_ret)
        drawdowns = cum_peak - cum_ret
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        dd_q = np.quantile(drawdowns, 1.0 - alpha) if len(drawdowns) > 0 else 0.0
        tail_dd = drawdowns[drawdowns >= dd_q]
        cdar_val = float(np.mean(tail_dd)) if len(tail_dd) > 0 else max_dd

        return {
            "var_99": round(max(0.0, var_val), 6),
            "cvar_99": round(max(0.0, cvar_val), 6),
            "max_drawdown": round(max(0.0, max_dd), 6),
            "cdar_99": round(max(0.0, cdar_val), 6)
        }

    def evaluate_marginal_cvar_contribution(
        self,
        returns_df: pd.DataFrame,
        current_weights: Dict[str, float],
        candidate_asset: str,
        candidate_weight: float = 0.15,
        max_cvar_increase_pct: float = 15.0
    ) -> Dict[str, Any]:
        """
        PB-118: Evalúa el impacto de incorporar una nueva estrategia candidata al portafolio.
        Si eleva el CVaR al 99% por encima del umbral máximo permitido, se veta la propuesta.
        """
        if candidate_asset not in returns_df.columns:
            return {"approved": False, "reason": "CANDIDATE_NOT_IN_RETURNS_DF"}

        # 1. Línea base de riesgo de cola
        base_risk = self.compute_portfolio_tail_risk(returns_df, current_weights, alpha=self.alpha)
        baseline_cvar = base_risk["cvar_99"]

        # 2. Simular inclusión del candidato con re-escalado proporcional
        scaled_weights = {k: v * (1.0 - candidate_weight) for k, v in current_weights.items()}
        scaled_weights[candidate_asset] = candidate_weight

        new_risk = self.compute_portfolio_tail_risk(returns_df, scaled_weights, alpha=self.alpha)
        new_cvar = new_risk["cvar_99"]

        # 3. Variación porcentual
        if baseline_cvar > 1e-6:
            delta_pct = ((new_cvar - baseline_cvar) / baseline_cvar) * 100.0
        else:
            delta_pct = 0.0

        approved = delta_pct <= max_cvar_increase_pct

        return {
            "approved": approved,
            "candidate": candidate_asset,
            "baseline_cvar_99": baseline_cvar,
            "new_cvar_99": new_cvar,
            "cvar_delta_pct": round(delta_pct, 2),
            "max_allowed_delta_pct": max_cvar_increase_pct,
            "decision": "APPROVED" if approved else "VETOED_EXCESSIVE_TAIL_RISK"
        }
