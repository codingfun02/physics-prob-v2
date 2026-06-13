"""1단계 — ρ 전이 스캔 실험 (시각화 및 순차 시뮬레이션)."""

from __future__ import annotations

import argparse
from pathlib import Path

from density.analytic import RHO_SCAN_SIM_NAMES, get_preset_rho, print_rho_scan_plan
from density.visualize import plot_rho_grid
from simulation.batch import allocate_workers, build_jobs, run_batch
from simulation.cancel import install_cancel_handler, is_cancel_requested, reset_cancel
from simulation.dashboard import build_dashboard
from simulation.output_layout import STUDY_RHO_SCAN, density_previews_dir
from simulation.run_descriptions import density_plot_title


def visualize_all_density(output_dir: Path | str | None = None) -> list[Path]:
    """ρ 스캔 7종 밀도 HTML."""
    output_dir = density_previews_dir(STUDY_RHO_SCAN, output_dir or "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    print_rho_scan_plan()
    print("=== 밀도 분포 시각화 ===")
    for i, name in enumerate(RHO_SCAN_SIM_NAMES, 1):
        grid = get_preset_rho(name)
        path = output_dir / f"{i:02d}_{name}.html"
        plot_rho_grid(grid, title=density_plot_title(name), save_path=path, show=False)
        paths.append(path)
        print(f"  [{i}/{len(RHO_SCAN_SIM_NAMES)}] {name}  ρ={grid.rho.max():.2f} → {path}")

    print(f"\n저장: {output_dir.resolve()}")
    return paths


def run_sequential_simulations(
    n_trials: int = 100_000,
    checkpoint_interval: int = 5000,
    output_dir: str = "output",
) -> list[dict]:
    """ρ 스캔 7종 순차 실행 → studies/rho_scan/factor/runs/{preset}/"""
    install_cancel_handler()
    reset_cancel()

    parallel_jobs, workers_per_sim = allocate_workers(len(RHO_SCAN_SIM_NAMES), parallel_jobs=1)

    print_rho_scan_plan()
    print("=== ρ 스캔 순차 시뮬레이션 ===")
    print(f"  시뮬 개수:    {len(RHO_SCAN_SIM_NAMES)}")
    print(f"  시행/시뮬:    {n_trials:,}")
    print(f"  저장 경로:    studies/rho_scan/factor/runs/{{preset}}/")
    print(f"  시뮬당 워커:  {workers_per_sim}개")
    for name in RHO_SCAN_SIM_NAMES:
        print(f"    {name}")

    jobs = build_jobs(
        RHO_SCAN_SIM_NAMES,
        n_trials=n_trials,
        workers_per_sim=workers_per_sim,
        output_dir=output_dir,
        checkpoint_interval=checkpoint_interval,
        study_id=STUDY_RHO_SCAN,
    )
    return run_batch(jobs, parallel_jobs=parallel_jobs)


def main():
    parser = argparse.ArgumentParser(description="1단계 ρ 스캔 실험")
    parser.add_argument("--visualize", action="store_true", help="밀도 HTML 생성")
    parser.add_argument("--run", action="store_true", help="순차 시뮬 실행")
    parser.add_argument("--plan", action="store_true", help="실험 설계만 출력")
    parser.add_argument("--trials", type=int, default=100_000)
    parser.add_argument("--checkpoint-interval", type=int, default=5000)
    args = parser.parse_args()

    if args.plan:
        print_rho_scan_plan()
        return

    if not args.visualize and not args.run:
        args.visualize = True

    if args.visualize:
        visualize_all_density()

    if args.run:
        results = run_sequential_simulations(
            n_trials=args.trials,
            checkpoint_interval=args.checkpoint_interval,
        )
        dash = build_dashboard(output_dir="output")
        if is_cancel_requested():
            print(f"\n중단됨 — {len(results)}개 저장")
        else:
            print(f"\n완료 — {len(results)}개")
        print(f"대시보드: {dash.resolve()}")


if __name__ == "__main__":
    main()
