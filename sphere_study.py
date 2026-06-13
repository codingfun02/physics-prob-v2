"""구 밀도 비교 실험 — 시각화 및 순차 배치 시뮬레이션."""

from __future__ import annotations

import argparse
from pathlib import Path

from density.analytic import (
    SPHERE_STUDY_SIM_NAMES,
    get_preset_rho,
)
from density.visualize import plot_rho_grid
from simulation.run_descriptions import density_plot_title
from simulation.batch import allocate_workers, build_jobs, run_batch
from simulation.cancel import install_cancel_handler, is_cancel_requested, reset_cancel
from simulation.output_layout import STUDY_SPHERE_LEGACY, density_previews_dir


def _preview_dir(output_dir: str | Path = "output") -> Path:
    return density_previews_dir(STUDY_SPHERE_LEGACY, output_dir)


def visualize_all_density(output_dir: Path | str | None = None) -> list[Path]:
    """7가지 밀도 분포 Plotly HTML을 만듭니다 (균일 + 구 6종)."""
    output_dir = _preview_dir(output_dir or "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    n_total = len(SPHERE_STUDY_SIM_NAMES)

    print("=== 구 밀도 실험 — 밀도 분포 시각화 ===")
    for i, name in enumerate(SPHERE_STUDY_SIM_NAMES, 1):
        grid = get_preset_rho(name)
        title = density_plot_title(name)
        path = output_dir / f"{i:02d}_{name}.html"
        plot_rho_grid(grid, title=title, save_path=path, show=False)
        paths.append(path)
        n_bump = int((grid.rho > 1.0).sum())
        print(
            f"  [{i}/{n_total}] {title}\n"
            f"        ρ 범위 {grid.rho.min():.2f}~{grid.rho.max():.2f}, "
            f"고밀도 셀 {n_bump}개 → {path}"
        )

    print(f"\n저장 폴더: {output_dir.resolve()}")
    return paths


def run_sequential_simulations(
    n_trials: int = 50000,
    checkpoint_interval: int = 5000,
    output_dir: str = "output",
) -> list[dict]:
    """7개 밀도(균일+구 6종)를 순차 실행 (한 번에 1개, 시뮬당 워커 최대)."""
    install_cancel_handler()
    reset_cancel()

    parallel_jobs, workers_per_sim = allocate_workers(
        len(SPHERE_STUDY_SIM_NAMES),
        parallel_jobs=1,
    )

    print("=== 구 밀도 실험 — 순차 시뮬레이션 ===")
    print(f"  시뮬 개수:    {len(SPHERE_STUDY_SIM_NAMES)} (균일 1 + 구 6)")
    print(f"  시행/시뮬:    {n_trials}")
    print(f"  동시 실행:    {parallel_jobs}개 (순차)")
    print(f"  시뮬당 워커:  {workers_per_sim}개")
    print("  중단:         Ctrl+C (1회=저장 후 종료, 2회=즉시 종료)")
    for i, name in enumerate(SPHERE_STUDY_SIM_NAMES, 1):
        print(f"  {sphere_study_title(i, name)}  [{name}]")

    jobs = build_jobs(
        SPHERE_STUDY_SIM_NAMES,
        n_trials=n_trials,
        workers_per_sim=workers_per_sim,
        output_dir=output_dir,
        checkpoint_interval=checkpoint_interval,
        study_id=STUDY_SPHERE_LEGACY,
    )
    return run_batch(jobs, parallel_jobs=parallel_jobs)


def main():
    parser = argparse.ArgumentParser(description="구 밀도 비교 실험")
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="7가지 밀도 분포 HTML만 생성",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="7가지 밀도 순차 시뮬레이션 실행",
    )
    parser.add_argument("--trials", type=int, default=50000)
    parser.add_argument("--checkpoint-interval", type=int, default=5000)
    args = parser.parse_args()

    if not args.visualize and not args.run:
        args.visualize = True

    if args.visualize:
        visualize_all_density()

    if args.run:
        results = run_sequential_simulations(
            n_trials=args.trials,
            checkpoint_interval=args.checkpoint_interval,
        )
        from simulation.dashboard import build_dashboard

        dash = build_dashboard(output_dir="output")
        if is_cancel_requested():
            print(f"\n중단됨 — {len(results)}개 시뮬 저장. 기록: output/history.json")
        else:
            print(f"\n완료 — {len(results)}개 시뮬. 기록: output/history.json")
        print(f"대시보드: {dash.resolve()}")


if __name__ == "__main__":
    main()
