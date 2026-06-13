"""시뮬레이션 1회 전체 파이프라인 (배치·단일 실행 공용)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config import OUTPUT_DIR
from density.analytic import get_preset_rho
from density.grid import RhoGrid
from simulation.charts import plot_probabilities, prob_y_axis_for_study
from simulation.run_descriptions import density_plot_title, probability_plot_title
from simulation.dashboard import build_dashboard
from simulation.monte_carlo import run_monte_carlo
from simulation.output_layout import (
    STUDY_CONTROLLED,
    preset_name_from_label,
    remove_study_density_preview,
    study_for_preset,
    variable_group_for_preset,
)
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
    study_id: str | None = None
    variable_group: str | None = None


def _build_grid(job: SimulationJob) -> RhoGrid:
    if job.rho_file:
        return RhoGrid.load(job.rho_file)
    preset_kw = {}
    if job.alpha is not None:
        preset_kw["alpha"] = job.alpha
    return get_preset_rho(job.rho_preset or job.rho_label, **preset_kw)


def run_full_simulation(job: SimulationJob) -> dict:
    """
    시뮬 1회: 몬테카를로 → HTML/JSON 저장 → history 등록.

    배치 워커 프로세스에서도 호출 가능.
    """
    out = Path(job.output_dir)
    out.mkdir(exist_ok=True)

    grid = _build_grid(job)
    rho_label = job.rho_label

    preset = job.rho_preset or preset_name_from_label(rho_label)
    vgroup = job.variable_group or variable_group_for_preset(preset, job.study_id)

    run_dir, run_id = create_run_directory(
        out,
        rho_label,
        study_id=job.study_id,
        variable_group=vgroup,
        preset_name=preset,
    )
    grid.save(run_dir / "rho_grid.npy")
    run_density_html = run_dir / "rho_density.html"
    from density.visualize import plot_rho_grid

    plot_rho_grid(
        grid,
        title=density_plot_title(rho_label),
        save_path=run_density_html,
        show=False,
    )

    mc = run_monte_carlo(
        grid,
        n_trials=job.n_trials,
        n_workers=job.n_workers,
        checkpoint_path=run_dir / "checkpoint.json",
        checkpoint_interval=job.checkpoint_interval,
        rho_name=rho_label,
    )
    probs, counts = mc.probs, mc.counts
    n_completed = mc.completed

    prob_html = run_dir / "face_probabilities.html"
    results_json = run_dir / "results.json"

    study_id = job.study_id or study_for_preset(preset) or STUDY_CONTROLLED
    y_range, y_dtick = prob_y_axis_for_study(
        out,
        study_id,
        extra=[(probs, n_completed)],
    )
    plot_probabilities(
        probs,
        n_completed,
        title=probability_plot_title(
            rho_label,
            n_completed,
            cancelled=mc.cancelled,
            target_trials=job.n_trials,
        ),
        save_path=prob_html,
        y_range=y_range,
        y_dtick=y_dtick,
    )
    save_results(
        results_json,
        counts=counts,
        n_trials=n_completed,
        rho_name=rho_label,
        extra={
            "alpha": job.alpha,
            "face": "bottom",
            "run_id": run_id,
            "target_trials": job.n_trials,
            "cancelled": mc.cancelled,
            "study_id": job.study_id,
            "variable_group": vgroup,
        },
    )
    if n_completed > 0:
        record_simulation_run(
            out,
            run_dir=run_dir,
            run_id=run_id,
            rho_name=rho_label,
            n_trials=n_completed,
            counts=counts,
            probs=probs,
            results_json=results_json,
            prob_html=prob_html,
            density_html=run_density_html,
            extra={
                "alpha": job.alpha,
                "face": "bottom",
                "target_trials": job.n_trials,
                "cancelled": mc.cancelled,
                "study_id": job.study_id,
                "variable_group": vgroup,
            },
        )
        if job.study_id and preset:
            if remove_study_density_preview(job.study_id, preset, out):
                print(f"  → 설계 미리보기 삭제 (시뮬 결과로 대체): {preset}")
        build_dashboard(out)

    if mc.cancelled:
        print(f"  → 중단됨: {n_completed}/{job.n_trials}회 완료, 결과 저장됨 → {run_dir}")

    return {
        "run_id": run_id,
        "rho_label": rho_label,
        "n_trials": n_completed,
        "target_trials": job.n_trials,
        "n_workers": job.n_workers,
        "probabilities": probs,
        "cancelled": mc.cancelled,
        "run_dir": str(run_dir),
        "results_json": str(results_json),
        "prob_html": str(prob_html),
    }
