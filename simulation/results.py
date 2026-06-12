"""시뮬레이션 결과 저장·불러오기."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def counts_to_probs(counts: dict[int, int], n_trials: int) -> dict[int, float]:
    return {face: counts[face] / n_trials for face in counts}


def standard_errors(probs: dict[int, float], n_trials: int) -> dict[int, float]:
    return {
        face: float(np.sqrt(probs[face] * (1 - probs[face]) / n_trials))
        for face in probs
    }


def save_results(
    path: str | Path,
    *,
    counts: dict[int, int],
    n_trials: int,
    rho_name: str,
    extra: dict | None = None,
) -> None:
    probs = counts_to_probs(counts, n_trials)
    se = standard_errors(probs, n_trials)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rho_name": rho_name,
        "n_trials": n_trials,
        "counts": {str(k): v for k, v in counts.items()},
        "probabilities": {str(k): v for k, v in probs.items()},
        "standard_errors": {str(k): v for k, v in se.items()},
        "extra": extra or {},
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def save_checkpoint(
    path: str | Path,
    *,
    counts: dict[int, int],
    completed: int,
    n_trials: int,
    rho_name: str,
) -> None:
    save_results(
        path,
        counts=counts,
        n_trials=completed,
        rho_name=rho_name,
        extra={"checkpoint": True, "target_trials": n_trials},
    )
