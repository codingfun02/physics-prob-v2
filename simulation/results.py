"""시뮬레이션 결과 저장·누적 히스토리."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


def counts_to_probs(counts: dict[int, int], n_trials: int) -> dict[int, float]:
    return {face: counts[face] / n_trials for face in counts}


def standard_errors(probs: dict[int, float], n_trials: int) -> dict[int, float]:
    return {
        face: float(np.sqrt(probs[face] * (1 - probs[face]) / n_trials))
        for face in probs
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run_directory(
    output_dir: str | Path,
    rho_label: str,
    *,
    study_id: str | None = None,
    variable_group: str | None = None,
    preset_name: str | None = None,
) -> tuple[Path, str]:
    """
    시행 폴더 생성.

    study_id·variable_group 지정 시:
      studies/{study}/{group}/runs/{preset}/
    미지정 시 (레거시):
      runs/{timestamp}_{label}/
    """
    from simulation.output_layout import grouped_run_dir, preset_name_from_label

    output_dir = Path(output_dir)
    preset = preset_name or preset_name_from_label(rho_label)

    if study_id and variable_group:
        run_dir = grouped_run_dir(study_id, variable_group, preset, output_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        run_id = f"{study_id}/{variable_group}/{preset}"
        return run_dir, run_id

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in rho_label)
    run_id = f"{ts}_{safe_label}"
    run_dir = output_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir, run_id


def save_results(
    path: str | Path,
    *,
    counts: dict[int, int],
    n_trials: int,
    rho_name: str,
    extra: dict | None = None,
) -> dict[str, Any]:
    """단일 JSON 파일 저장. payload dict 반환."""
    probs = counts_to_probs(counts, n_trials)
    se = standard_errors(probs, n_trials)
    payload = {
        "timestamp": _now_iso(),
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
    return payload


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


def load_history(output_dir: str | Path) -> dict[str, Any]:
    """누적 히스토리 로드. 없으면 빈 목록."""
    path = Path(output_dir) / "history.json"
    if not path.exists():
        return {"runs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def append_run_history(
    output_dir: str | Path,
    entry: dict[str, Any],
) -> Path:
    """history.json에 시행 기록 추가."""
    output_dir = Path(output_dir)
    history_path = output_dir / "history.json"
    history = load_history(output_dir)
    history["runs"].append(entry)
    history["last_updated"] = _now_iso()
    history_path.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return history_path


def record_simulation_run(
    output_dir: str | Path,
    *,
    run_dir: Path,
    run_id: str,
    rho_name: str,
    n_trials: int,
    counts: dict[int, int],
    probs: dict[int, float],
    results_json: Path,
    prob_html: Path,
    density_html: Path | None = None,
    extra: dict | None = None,
) -> Path:
    """
    시뮬 1회분을 history.json에 등록.

    run_dir 안에 이미 results.json, face_probabilities.html이 있어야 함.
    """
    entry = {
        "run_id": run_id,
        "timestamp": _now_iso(),
        "rho_name": rho_name,
        "n_trials": n_trials,
        "probabilities": {str(k): round(v, 6) for k, v in probs.items()},
        "counts": {str(k): v for k, v in counts.items()},
        "paths": {
            "run_dir": str(run_dir.as_posix()),
            "results_json": str(results_json.as_posix()),
            "face_probabilities_html": str(prob_html.as_posix()),
        },
        "extra": extra or {},
    }
    if density_html is not None:
        entry["paths"]["rho_density_html"] = str(density_html.as_posix())

    return append_run_history(output_dir, entry)
