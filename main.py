"""주사위 확률분포 시뮬레이션 — CLI 진입점."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from config import OUTPUT_DIR
from density.analytic import PRESETS, get_preset_rho
from density.grid import RhoGrid
from density.visualize import plot_rho_grid
from simulation.monte_carlo import run_monte_carlo
from simulation.results import save_results
from simulation.single_trial import run_single_trial


def plot_probabilities(probs: dict[int, float], n_trials: int, title: str, save_path: Path):
    """Plotly 막대그래프 (matplotlib 대신 — Windows 보안 정책 호환)."""
    import plotly.graph_objects as go

    faces = list(range(1, 7))
    p = [probs[f] for f in faces]
    err = [np.sqrt(p_i * (1 - p_i) / n_trials) for p_i in p]

    fig = go.Figure(
        data=[
            go.Bar(x=faces, y=p, error_y=dict(type="data", array=err), name="확률"),
            go.Scatter(
                x=faces,
                y=[1 / 6] * 6,
                mode="lines",
                line=dict(color="red", dash="dash"),
                name="균일 (1/6)",
            ),
        ]
    )
    fig.update_layout(
        title=title,
        xaxis_title="눈 (위쪽 면)",
        yaxis_title="확률",
        yaxis_range=[0, max(p) * 1.3 + 0.05],
    )
    html_path = save_path.with_suffix(".html")
    fig.write_html(str(html_path))


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
    if args.rho_file:
        grid = RhoGrid.load(args.rho_file)
        rho_label = Path(args.rho_file).stem
    else:
        preset_kw = {}
        if args.alpha is not None:
            preset_kw["alpha"] = args.alpha
            rho_label = f"{args.rho}_alpha{args.alpha}"
        grid = get_preset_rho(args.rho, **preset_kw)

    print(grid)
    grid.save(out / "rho_grid.npy")
    plot_rho_grid(grid, title=f"밀도 분포: {rho_label}", save_path=out / "rho_density.html", show=False)
    print(f"3D 밀도 그래프: {out / 'rho_density.html'}")

    if args.visualize_only:
        return

    if args.single_test:
        face = run_single_trial(grid, seed=42)
        print(f"1회 시험 결과 — 위쪽 면: {face}")
        return

    print(f"\n{args.trials}회 시뮬레이션 시작...")
    probs, counts = run_monte_carlo(
        grid,
        n_trials=args.trials,
        n_workers=args.workers,
        checkpoint_path=out / "checkpoint.json",
        checkpoint_interval=args.checkpoint_interval,
        rho_name=rho_label,
    )

    print("\n=== 결과 ===")
    for f in range(1, 7):
        print(f"  눈 {f}: {probs[f]:.4f} ({probs[f]*100:.2f}%)")

    plot_probabilities(
        probs,
        args.trials,
        title=f"주사위 확률분포 ({rho_label}, N={args.trials})",
        save_path=out / "face_probabilities.html",
    )
    save_results(
        out / "results.json",
        counts=counts,
        n_trials=args.trials,
        rho_name=rho_label,
        extra={"alpha": args.alpha},
    )
    print(f"확률 그래프: {out / 'face_probabilities.html'}")
    print(f"결과 JSON: {out / 'results.json'}")


if __name__ == "__main__":
    main()
