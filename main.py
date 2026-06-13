"""주사위 확률분포 시뮬레이션 — CLI 진입점."""

from __future__ import annotations

import argparse
from pathlib import Path

from config import OUTPUT_DIR
from density.analytic import PRESETS, get_preset_rho
from density.grid import RhoGrid
from density.visualize import plot_rho_grid
from simulation.cancel import install_cancel_handler, reset_cancel
from simulation.output_layout import adhoc_preview_path, dashboard_path
from simulation.run_descriptions import density_plot_title
from simulation.pipeline import SimulationJob, run_full_simulation
from simulation.single_trial import run_single_trial


def main():
    parser = argparse.ArgumentParser(description="비균일 밀도 주사위 몬테카를로 시뮬레이션")
    parser.add_argument("--rho", default="uniform", choices=list(PRESETS.keys()))
    parser.add_argument("--rho-file", type=str, help=".npy 밀도 격자 파일")
    parser.add_argument("--alpha", type=float, default=None, help="linear_x, layer 프리셋 기울기")
    parser.add_argument("--trials", type=int, default=50000)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--checkpoint-interval", type=int, default=1000)
    parser.add_argument("--visualize-only", action="store_true")
    parser.add_argument("--single-test", action="store_true", help="1회만 시험")
    args = parser.parse_args()

    out = Path(OUTPUT_DIR)
    out.mkdir(exist_ok=True)

    rho_label = args.rho
    rho_preset = args.rho
    rho_file = None
    if args.rho_file:
        grid = RhoGrid.load(args.rho_file)
        rho_label = Path(args.rho_file).stem
        rho_preset = None
        rho_file = args.rho_file
    else:
        preset_kw = {}
        if args.alpha is not None:
            preset_kw["alpha"] = args.alpha
            rho_label = f"{args.rho}_alpha{args.alpha}"
        grid = get_preset_rho(args.rho, **preset_kw)

    print(grid)

    preview_density = adhoc_preview_path(rho_label, out)
    preview_density.parent.mkdir(parents=True, exist_ok=True)
    plot_rho_grid(grid, title=density_plot_title(rho_label), save_path=preview_density, show=False)
    print(f"3D 밀도 그래프 (미리보기): {preview_density}")

    if args.visualize_only:
        return

    if args.single_test:
        face = run_single_trial(grid, seed=42)
        print(f"1회 시험 결과 — 바닥의 눈: {face}")
        return

    from multiprocessing import cpu_count

    n_workers = args.workers if args.workers is not None else max(1, cpu_count() - 1)

    job = SimulationJob(
        rho_label=rho_label,
        rho_preset=rho_preset,
        rho_file=rho_file,
        alpha=args.alpha,
        n_trials=args.trials,
        n_workers=n_workers,
        output_dir=str(out),
        checkpoint_interval=args.checkpoint_interval,
    )

    install_cancel_handler()
    reset_cancel()

    print(f"\n{args.trials}회 시뮬레이션 시작 (워커 {n_workers}개)...")
    result = run_full_simulation(job)

    print("\n=== 결과 (바닥의 눈) ===")
    for f in range(1, 7):
        p = result["probabilities"][f]
        print(f"  바닥의 눈 {f}: {p:.4f} ({p*100:.2f}%)")

    print(f"\n이번 시행 저장:")
    print(f"  시행 ID:     {result['run_id']}")
    print(f"  확률 그래프: {result['prob_html']}")
    print(f"  결과 JSON:   {result['results_json']}")
    print(f"  누적 목록:   {out / 'history.json'}")
    print(f"  대시보드:    {dashboard_path(out)}")


if __name__ == "__main__":
    main()
