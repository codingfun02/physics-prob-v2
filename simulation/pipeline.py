"""시뮬레이션 1회 전체 파이프라인 (배치·단일 실행 공용)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from config import OUTPUT_DIR
from density.analytic import get_preset_rho
from density.grid import RhoGrid
from density.visualize import plot_rho_grid
from simulation.monte_carlo import run_monte_carlo
from simulation.results import create_run_directory, record_simulation_run, save_results


@dataclass
class SimulationJob:
    """배치 실행용 설정 (pickle 가능)."""

    rho_label: str
    n_trials: int
    n_workers: int
    output_dir: str = OUTPUT_DIR
    rho_preset: str | None = None
    rho_file: str | None = None
    alpha: float | None = None
    checkpoint_interval: int = 1000


def _build_grid(job: SimulationJob) -> RhoGrid:
    if job.rho_file:
        return RhoGrid.load(job.rho_file)
    preset_kw = {}
    if job.alpha is not None:
        preset_kw["alpha"] = job.alpha
    return get_preset_rho(job.rho_preset or job.rho_label, **preset_kw)


def plot_probabilities(probs: dict[int, float], n_trials: int, title: str, save_path: Path):
    import plotly.graph_objects as go

    faces = list(range(1, 7))
    p = [probs[f] for f in faces]
    err = [((p_i * (1 - p_i) / n_trials) ** 0.5) for p_i in p]

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
        xaxis_title="바닥의 눈",
        yaxis_title="확률",
        yaxis_range=[0, max(p) * 1.3 + 0.05],
    )
    fig.write_html(str(save_path))


def run_full_simulation(job: SimulationJob) -> dict:
    """
    시뮬 1회: 몬테카를로 → HTML/JSON 저장 → history 등록.

    배치 워커 프로세스에서도 호출 가능.
    """
    out = Path(job.output_dir)
    out.mkdir(exist_ok=True)

    grid = _build_grid(job)
    rho_label = job.rho_label

    preview_density = out / f"rho_density_{rho_label}.html"
    plot_rho_grid(grid, title=f"밀도 분포: {rho_label}", save_path=preview_density, show=False)

    run_dir, run_id = create_run_directory(out, rho_label)
    grid.save(run_dir / "rho_grid.npy")
    run_density_html = run_dir / "rho_density.html"
    shutil.copy2(preview_density, run_density_html)

    probs, counts = run_monte_carlo(
        grid,
        n_trials=job.n_trials,
        n_workers=job.n_workers,
        checkpoint_path=run_dir / "checkpoint.json",
        checkpoint_interval=job.checkpoint_interval,
        rho_name=rho_label,
    )

    prob_html = run_dir / "face_probabilities.html"
    results_json = run_dir / "results.json"

    plot_probabilities(
        probs,
        job.n_trials,
        title=f"바닥의 눈 확률분포 ({rho_label}, N={job.n_trials})",
        save_path=prob_html,
    )
    save_results(
        results_json,
        counts=counts,
        n_trials=job.n_trials,
        rho_name=rho_label,
        extra={"alpha": job.alpha, "face": "bottom", "run_id": run_id},
    )
    record_simulation_run(
        out,
        run_dir=run_dir,
        run_id=run_id,
        rho_name=rho_label,
        n_trials=job.n_trials,
        counts=counts,
        probs=probs,
        results_json=results_json,
        prob_html=prob_html,
        density_html=run_density_html,
        extra={"alpha": job.alpha, "face": "bottom"},
    )

    return {
        "run_id": run_id,
        "rho_label": rho_label,
        "n_trials": job.n_trials,
        "n_workers": job.n_workers,
        "probabilities": probs,
        "run_dir": str(run_dir),
        "results_json": str(results_json),
        "prob_html": str(prob_html),
    }
