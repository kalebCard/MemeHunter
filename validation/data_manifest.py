"""
Módulo de Versionado Inmutable de Datasets, Checksums y Gobernanza de Reproducibilidad MLOps.
US-4.3 (Sprint 4).

Garantiza reproducibilidad matemática institucional registrando:
- Hash criptográfico SHA-256 inmutable de datasets (OHLCV DataFrames / archivos).
- Rango temporal estricto (start_time, end_time), dimensiones y nombres de columnas.
- Hash de commit Git activo y estado del repositorio.
- Fijación determinista de semillas pseudoaleatorias en numpy, random y entorno.
- Exportación estructurada de run_metadata.json para auditoría cuantitativa y regulatoria.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
import hashlib
import json
import os
import random
import subprocess
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd


def set_global_seed(seed: int = 42) -> int:
    """
    Fija de forma determinista la semilla pseudoaleatoria en todos los generadores del proceso.
    """
    int_seed = int(seed)
    random.seed(int_seed)
    np.random.seed(int_seed)
    os.environ["PYTHONHASHSEED"] = str(int_seed)
    return int_seed


def get_git_commit_hash(repo_dir: Optional[str] = None) -> str:
    """
    Obtiene el commit SHA de Git actual o retorna un identificador de contingencia.
    """
    cwd = repo_dir or os.getcwd()
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return os.environ.get("GIT_COMMIT_SHA", "git_commit_untracked_2026")


@dataclass
class DatasetManifest:
    """Manifiesto criptográfico inmutable de un dataset de mercado."""
    dataset_sha256: str
    n_rows: int
    n_cols: int
    columns: List[str]
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    symbols: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RunMetadata:
    """Metadatos completos de auditoría cuantitativa y reproducibilidad de una ejecución."""
    run_id: str
    timestamp_utc: str
    git_commit: str
    random_seed: int
    data_manifest: DatasetManifest
    hyperparameters: Dict[str, Any]
    validation_metrics: Dict[str, Any] = field(default_factory=dict)
    factors_discovered_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data

    def save_json(self, filepath: str) -> None:
        """Persiste los metadatos en un archivo JSON atómico/estructurado."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_json(cls, filepath: str) -> "RunMetadata":
        """Carga y reconstruye la instancia de metadatos desde JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            d = json.load(f)
        manifest_data = d.pop("data_manifest")
        manifest = DatasetManifest(**manifest_data)
        return cls(data_manifest=manifest, **d)


class DataManifestEngine:
    """
    Motor institucional de hashing y control de reproducibilidad para datos y ejecuciones.
    """

    @staticmethod
    def compute_dataframe_sha256(df: pd.DataFrame) -> str:
        """
        Calcula un hash SHA-256 determinista del contenido y estructura de un DataFrame.
        """
        hasher = hashlib.sha256()
        # Hash de nombres y orden de columnas
        cols_repr = ",".join(str(c) for c in df.columns).encode("utf-8")
        hasher.update(cols_repr)

        # Hash determinista de los valores numéricos/textuales
        # Para consistencia entre plataformas, serializar via array buffer o parquet/feather
        try:
            # Serialización binaria determinista de arrays de numpy
            for col in df.columns:
                series = df[col]
                hasher.update(col.encode("utf-8"))
                if pd.api.types.is_numeric_dtype(series):
                    arr = np.ascontiguousarray(series.to_numpy(dtype=np.float64, na_value=np.nan))
                    # Normalizar NaNs a representación binaria estándar
                    arr_bytes = np.nan_to_num(arr, nan=-999999.999).tobytes()
                    hasher.update(arr_bytes)
                else:
                    str_repr = "\n".join(series.astype(str)).encode("utf-8")
                    hasher.update(str_repr)
        except Exception:
            # Fallback seguro
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            hasher.update(csv_bytes)

        return hasher.hexdigest()

    @classmethod
    def generate_manifest(cls, df: pd.DataFrame, symbols: Optional[List[str]] = None) -> DatasetManifest:
        """
        Genera el manifiesto criptográfico a partir de un DataFrame de precios/volumen.
        """
        sha = cls.compute_dataframe_sha256(df)
        start_ts = None
        end_ts = None

        if "date" in df.columns:
            start_ts = str(df["date"].iloc[0])
            end_ts = str(df["date"].iloc[-1])
        elif isinstance(df.index, pd.DatetimeIndex):
            start_ts = str(df.index[0])
            end_ts = str(df.index[-1])
        elif "timestamp" in df.columns:
            start_ts = str(df["timestamp"].iloc[0])
            end_ts = str(df["timestamp"].iloc[-1])

        detected_symbols = list(symbols or [])
        if not detected_symbols and "symbol" in df.columns:
            detected_symbols = sorted(list(df["symbol"].dropna().unique().astype(str)))

        return DatasetManifest(
            dataset_sha256=sha,
            n_rows=len(df),
            n_cols=len(df.columns),
            columns=list(df.columns.astype(str)),
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            symbols=detected_symbols
        )

    @classmethod
    def build_run_metadata(
        cls,
        df: pd.DataFrame,
        hyperparameters: Dict[str, Any],
        random_seed: int = 42,
        validation_metrics: Optional[Dict[str, Any]] = None,
        factors_discovered_count: int = 0,
        run_id_prefix: str = "GEN_RUN"
    ) -> RunMetadata:
        """
        Construye el registro integral de metadatos de una ejecución MLOps.
        """
        manifest = cls.generate_manifest(df)
        now_utc = datetime.now(timezone.utc).isoformat()
        git_hash = get_git_commit_hash()
        run_id = f"{run_id_prefix}_{random_seed}_{now_utc[:10].replace('-', '')}_{manifest.dataset_sha256[:8]}"

        return RunMetadata(
            run_id=run_id,
            timestamp_utc=now_utc,
            git_commit=git_hash,
            random_seed=int(random_seed),
            data_manifest=manifest,
            hyperparameters=hyperparameters,
            validation_metrics=validation_metrics or {},
            factors_discovered_count=factors_discovered_count
        )
