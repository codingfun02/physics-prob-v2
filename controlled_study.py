"""변인 통제 구 밀도 실험 — 시각화 및 순차 시뮬레이션."""

from __future__ import annotations

import argparse
from pathlib import Path

from density.analytic import (
    CONTROLLED_STUDY_SIM_NAMES,
    controlled_study_title,
    get_preset_rho,
    lookup_controlled_spec,
    print_controlled_study_plan,
)
from density.visualize import plot_rho_grid
from simulation.run_descriptions import density_plot_title
from simulation.batch import allocate_workers, build_jobs, run_batch
from simulation.cancel import install_cancel_handler, is_cancel_requested, reset_cancel
from simulation.output_layout import STUDY_CONTROLLED, density_previews_dir


def _preview_dir(output_dir: str | Path = "output") -> Path:
    return density_previews_dir(STUDY_CONTROLLED, output_dir)


def visualize_all_density(output_dir: Path | str | None = None) -> list[Path]:
    """10가지 밀도 분포 HTML (균일 + 변인 통제 9종)."""
    output_dir = _preview_dir(output_dir or "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    n_total = len(CONTROLLED_STUDY_SIM_NAMES)

    print_controlled_study_plan()
    print("=== 밀도 분포 시각화 ===")
    for i, name in enumerate(CONTROLLED_STUDY_SIM_NAMES, 1):
        grid = get_preset_rho(name)
        title = density_plot_title(name)
        path = output_dir / f"{i:02d}_{name}.html"
        plot_rho_grid(grid, title=title, save_path=path, show=False)
        paths.append(path)
        n_bump = int((grid.rho > 1.0).sum())
        print(
            f"  [{i}/{n_total}] {title}\n"
            f"        ρ {grid.rho.min():.2f}~{grid.rho.max():.2f}, "
            f"고밀도 셀 {n_bump}개 → {path}"
        )

    print(f"\n저장: {output_dir.resolve()}")
    return paths


def run_sequential_simulations(
    n_trials: int = 50000,
    checkpoint_interval: int = 5000,
    output_dir: str = "output",
) -> list[dict]:
    """균일 + 변인 통제 9종 순차 실행."""
    install_cancel_handler()
    reset_cancel()

    parallel_jobs, workers_per_sim = allocate_workers(
        len(CONTROLLED_STUDY_SIM_NAMES),
        parallel_jobs=1,
    )

    print_controlled_study_plan()
    print("=== 순차 시뮬레이션 ===")
    print(f"  시뮬 개수:    {len(CONTROLLED_STUDY_SIM_NAMES)} (균일 1 + 구 9)")
    print(f"  시행/시뮬:    {n_trials}")
    print(f"  시뮬당 워커:  {workers_per_sim}개")
    print("  중단:         Ctrl+C (1회=저장 후 종료)")
    for i, name in enumerate(CONTROLLED_STUDY_SIM_NAMES, 1):
        spec = lookup_controlled_spec(name)
        title = (
            f"{i}. {controlled_study_title(spec)}"
            if spec
            else f"{i}. {name}"
        )
        print(f"  {title}  [{name}]")

    jobs = build_jobs(
        CONTROLLED_STUDY_SIM_NAMES,
        n_trials=n_trials,
        workers_per_sim=workers_per_sim,
        output_dir=output_dir,
        checkpoint_interval=checkpoint_interval,
        study_id=STUDY_CONTROLLED,
    )
    return run_batch(jobs, parallel_jobs=parallel_jobs)


def main():
    parser = argparse.ArgumentParser(description="변인 통제 구 밀도 실험")
    parser.add_argument("--visualize", action="store_true", help="밀도 HTML 생성")
    parser.add_argument("--run", action="store_true", help="순차 시뮬 실행")
    parser.add_argument("--plan", action="store_true", help="실험 설계만 출력")
    parser.add_argument("--trials", type=int, default=50000)
    parser.add_argument("--checkpoint-interval", type=int, default=5000)
    args = parser.parse_args()

    if args.plan:
        print_controlled_study_plan()
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
        from simulation.dashboard import build_dashboard

        dash = build_dashboard(output_dir="output")
        if is_cancel_requested():
            print(f"\n중단됨 — {len(results)}개 저장. history.json")
        else:
            print(f"\n완료 — {len(results)}개. history.json")
        print(f"대시보드: {dash.resolve()}")


if __name__ == "__main__":
    main()
