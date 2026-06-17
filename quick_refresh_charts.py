"""차트만 빠르게 재생성 (전체 refresh-density/chart 대신).

사용법:
  run.bat quick_refresh_charts.py --all-runs --density-only
  run.bat quick_refresh_charts.py --preset ctrl_factor_f30
  run.bat quick_refresh_charts.py --all-runs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from config import OUTPUT_DIR
from density.analytic import get_preset_rho
from density.grid import RhoGrid
from density.visualize import plot_rho_grid
from simulation.charts import (
    plot_probabilities,
    prob_y_axes_by_study,
    prob_series,
    study_from_results,
    unify_prob_y_axis,
)
from simulation.dashboard import build_dashboard
from simulation.output_layout import ARCHIVED_STUDY_IDS


def _iter_run_dirs(out: Path):
    """output/runs 및 studies/**/runs 시뮬 폴더."""
    runs_root = out / "runs"
    if runs_root.is_dir():
        for run_dir in sorted(runs_root.iterdir()):
            if run_dir.is_dir():
                yield run_dir
    studies_root = out / "studies"
    if studies_root.is_dir():
        for results_path in sorted(studies_root.rglob("results.json")):
            yield results_path.parent
from simulation.run_descriptions import density_plot_title, probability_plot_title


def _regenerate_density(name: str, save_path: Path) -> None:
    grid = get_preset_rho(name)
    plot_rho_grid(grid, title=density_plot_title(name), save_path=save_path, show=False)
    print(f"  질량: {save_path}")


def _regenerate_run_density(run_dir: Path, *, force: bool = False) -> None:
    npy = run_dir / "rho_grid.npy"
    if not npy.exists():
        return
    out = run_dir / "rho_density.html"
    if not force and out.exists() and out.stat().st_mtime >= npy.stat().st_mtime:
        return
    rho_name = run_dir.name.split("_", 2)[-1] if "_" in run_dir.name else run_dir.name
    results_path = run_dir / "results.json"
    if results_path.exists():
        data = json.loads(results_path.read_text(encoding="utf-8"))
        rho_name = data.get("rho_name", rho_name)
    grid = RhoGrid.load(npy)
    out = run_dir / "rho_density.html"
    plot_rho_grid(grid, title=density_plot_title(rho_name), save_path=out, show=False)
    print(f"  질량: {out}")


def _regenerate_prob(
    run_dir: Path,
    study_axes: dict[str, tuple[list[float], float]] | None = None,
    *,
    force: bool = False,
) -> None:
    results_path = run_dir / "results.json"
    if not results_path.exists():
        print(f"  건너뜀 (확률 없음): {run_dir}")
        return
    out = run_dir / "face_probabilities.html"
    if not force and out.exists() and out.stat().st_mtime >= results_path.stat().st_mtime:
        return
    data = json.loads(results_path.read_text(encoding="utf-8"))
    probs = {int(k): float(v) for k, v in data["probabilities"].items()}
    n_trials = int(data["n_trials"])
    extra = data.get("extra") or {}
    sid = study_from_results(data)
    if study_axes and sid in study_axes:
        y_range, y_dtick = study_axes[sid]
    else:
        y_range, y_dtick = unify_prob_y_axis([prob_series(probs, n_trials)])
    out = run_dir / "face_probabilities.html"
    plot_probabilities(
        probs,
        n_trials,
        probability_plot_title(
            data["rho_name"],
            n_trials,
            cancelled=extra.get("cancelled"),
            target_trials=extra.get("target_trials", n_trials),
        ),
        out,
        y_range=y_range,
        y_dtick=y_dtick,
    )
    print(f"  확률: {out}")


def _regenerate_run(
    run_dir: Path,
    study_axes: dict[str, tuple[list[float], float]] | None = None,
    *,
    force: bool = False,
) -> None:
    _regenerate_run_density(run_dir, force=force)
    _regenerate_prob(run_dir, study_axes, force=force)


def main() -> None:
    parser = argparse.ArgumentParser(description="선택 차트만 빠르게 재생성")
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--preset", default="ctrl_factor_f30", help="밀도 프리셋 이름")
    parser.add_argument("--all-previews", action="store_true", help="studies/*/density_previews 전부")
    parser.add_argument("--all-runs", action="store_true", help="모든 시뮬 run 질량·확률 차트")
    parser.add_argument(
        "--study",
        default=None,
        help="특정 study만 확률 차트 재생성 (예: controlled_v3)",
    )
    parser.add_argument(
        "--prob-only",
        action="store_true",
        help="확률(HTML+PNG)만 재생성",
    )
    parser.add_argument(
        "--density-only",
        action="store_true",
        help="질량분포(HTML+PNG)만 재생성 (--all-runs 와 함께)",
    )
    args = parser.parse_args()
    out = Path(args.output_dir)

    if args.density_only:
        print("질량분포 재생성…")
        for run_dir in _iter_run_dirs(out):
            _regenerate_run_density(run_dir, force=True)
        print("완료")
        return

    study_axes = prob_y_axes_by_study(out)

    if args.study:
        print(f"확률 차트 재생성 ({args.study})…")
        for run_dir in _iter_run_dirs(out):
            results_path = run_dir / "results.json"
            if not results_path.exists():
                continue
            data = json.loads(results_path.read_text(encoding="utf-8"))
            if study_from_results(data) != args.study:
                continue
            if args.prob_only:
                _regenerate_prob(run_dir, study_axes, force=True)
            else:
                _regenerate_run(run_dir, study_axes, force=True)
        print("대시보드 갱신…")
        path = build_dashboard(out)
        print(f"완료: {path}")
        return

    print("차트 재생성…")
    if args.all_previews:
        for previews in sorted((out / "studies").glob("*/density_previews")):
            if previews.parent.name in ARCHIVED_STUDY_IDS:
                continue
            for html in sorted(previews.glob("*.html")):
                stem = html.stem
                name = "_".join(stem.split("_")[1:]) if stem[:2].isdigit() else stem
                _regenerate_density(name, html)
    elif not args.all_runs:
        for run_dir in sorted((out / "runs").glob(f"*_{args.preset}")):
            if run_dir.is_dir():
                _regenerate_run(run_dir, study_axes, force=True)

    if args.all_runs:
        for run_dir in _iter_run_dirs(out):
            if args.prob_only:
                _regenerate_prob(run_dir, study_axes, force=True)
            else:
                _regenerate_run(run_dir, study_axes, force=True)

    print("대시보드 갱신…")
    path = build_dashboard(out)
    print(f"완료: {path}")


if __name__ == "__main__":
    main()
