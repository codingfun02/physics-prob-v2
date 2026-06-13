"""history.json 기록으로 삭제된 runs/ 폴더·HTML 복구."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from config import OUTPUT_DIR
from density.analytic import get_preset_rho
from density.visualize import plot_rho_grid
from simulation.charts import plot_probabilities
from simulation.run_descriptions import density_plot_title, probability_plot_title
from simulation.dashboard import build_dashboard
from simulation.results import load_history, save_results


def recover_run(run: dict, output_dir: Path, *, force: bool) -> Path:
    run_id = run["run_id"]
    run_dir = output_dir / "runs" / run_id
    if run_dir.exists() and not force:
        if (run_dir / "results.json").exists():
            return run_dir
    run_dir.mkdir(parents=True, exist_ok=True)

    counts = {int(k): int(v) for k, v in run["counts"].items()}
    n_trials = int(run["n_trials"])
    rho_name = run["rho_name"]
    extra = dict(run.get("extra") or {})
    extra.setdefault("run_id", run_id)
    extra.setdefault("recovered_from_history", True)

    results_json = run_dir / "results.json"
    payload = save_results(
        results_json,
        counts=counts,
        n_trials=n_trials,
        rho_name=rho_name,
        extra=extra,
    )
    payload["timestamp"] = run.get("timestamp", payload["timestamp"])

    probs = {int(k): float(v) for k, v in run["probabilities"].items()}
    plot_probabilities(
        probs,
        n_trials,
        title=probability_plot_title(rho_name, n_trials),
        save_path=run_dir / "face_probabilities.html",
    )

    grid = get_preset_rho(rho_name)
    grid.save(run_dir / "rho_grid.npy")
    plot_rho_grid(
        grid,
        title=density_plot_title(rho_name),
        save_path=run_dir / "rho_density.html",
        show=False,
    )
    return run_dir


def main():
    parser = argparse.ArgumentParser(description="history.json에서 runs/ 복구")
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--min-trials", type=int, default=0, help="이 값 이상만 복구")
    parser.add_argument("--force", action="store_true", help="기존 run 폴더 덮어쓰기")
    parser.add_argument("--no-dashboard", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    history = load_history(output_dir)
    runs = history.get("runs", [])
    targets = [r for r in runs if r.get("n_trials", 0) >= args.min_trials]

    print(f"복구 대상: {len(targets)}개 (전체 {len(runs)}개)")
    for run in targets:
        path = recover_run(run, output_dir, force=args.force)
        print(f"  ✓ {run['run_id']}  N={run['n_trials']}  → {path}")

    root_history = Path("history.json")
    out_history = output_dir / "history.json"
    if root_history.exists() and out_history.exists():
        if root_history.stat().st_mtime < out_history.stat().st_mtime:
            shutil.copy2(out_history, root_history)
            print(f"\n프로젝트 루트 history.json 갱신 ({len(targets)}개 기록 반영)")

    if not args.no_dashboard:
        dash = build_dashboard(output_dir)
        print(f"대시보드: {dash.resolve()}")


if __name__ == "__main__":
    main()
