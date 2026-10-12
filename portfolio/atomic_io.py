"""
atomic_io.py - Persistencia Atómica Transaccional de Archivos JSON (US-4.1).

Garantiza que las escrituras a disco de estados críticos (incubadora, archivo de nichos,
autopsias, ratchet, bóveda) se realicen primero sobre un archivo temporal (.tmp)
y se reemplacen de manera atómica con os.replace(), evitando corrupción de datos
o archivos truncados a 0 bytes ante interrupciones de proceso.
"""

import os
import json
from pathlib import Path
from typing import Any, Union


def atomic_write_json(filepath: Union[str, Path], data: Any, indent: int = 2) -> None:
    """
    Escribe datos estructurados en formato JSON de manera transaccional y atómica.
    
    1. Asegura la existencia del directorio padre.
    2. Escribe el contenido en un archivo temporal (.tmp).
    3. Ejecuta flush() y fsync() para vaciar los buffers del sistema operativo.
    4. Reemplaza atómicamente el archivo destino con os.replace().
    """
    target_path = Path(filepath).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_name(f"{target_path.name}.tmp")

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_path, target_path)
