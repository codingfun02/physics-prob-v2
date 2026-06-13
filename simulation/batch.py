"""여러 시뮬레이션을 순차 또는 병렬로 실행."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

from density.analytic import PRESETS
from simulation.output_layout import variable_group_for_preset
from simulation.pipeline import SimulationJob, run_full_simulation


def allocate_workers(
    n_simulations: int,
    parallel_jobs: int | None = None,
    total_workers: int | None = None,
) -> tuple[int, int]:
    """
    CPU 코어를 시뮬 개수에 나눠 (동시 실행 수, 시뮬당 워커 수) 반환.

    원칙:
    - 코어를 너무 많이 나누면 시뮬당 PyBullet 워커가 줄어 느려짐
    - 동시에 너무 많이 돌리면 CPU 경쟁으로 전체가 느려짐
    - 시뮬당 워커 최소 2 권장 (가능할 때)
    """
    cpus = cpu_count()
    usable = total_workers if total_workers is not None else max(1, cpus - 1)

    if parallel_jobs is None or parallel_jobs <= 0:
        # 자동: 시뮬당 최소 2워커, 동시 실행은 usable//2 이하
        parallel_jobs = min(n_simulations, max(1, usable // 2))
    parallel_jobs = min(parallel_jobs, n_simulations)
    parallel_jobs = max(1, parallel_jobs)

    workers_per_sim = max(1, usable // parallel_jobs)
    return parallel_jobs, workers_per_sim


def build_jobs(
    rho_names: list[str],
    n_trials: int,
    workers_per_sim: int,
    alpha: float | None = None,
    output_dir: str | None = None,
    checkpoint_interval: int = 1000,
    study_id: str | None = None,
) -> list[SimulationJob]:
    jobs = []
    for name in rho_names:
        if name not in PRESETS:
            raise ValueError(f"Unknown preset '{name}'. Choose from {list(PRESETS)}")
        label = f"{name}_alpha{alpha}" if alpha is not None else name
        jobs.append(
            SimulationJob(
                rho_label=label,
                rho_preset=name,
                n_trials=n_trials,
                n_workers=workers_per_sim,
                alpha=alpha,
                output_dir=output_dir or "output",
                checkpoint_interval=checkpoint_interval,
                study_id=study_id,
                variable_group=variable_group_for_preset(name, study_id),
            )
        )
    return jobs


def run_batch(
    jobs: list[SimulationJob],
    parallel_jobs: int = 1,
) -> list[dict]:
    """
    여러 시뮬 실행.

    parallel_jobs=1 → 순차 (시뮬당 워커 최대 활용)
    parallel_jobs>1 → 동시에 여러 시뮬 (시뮬당 워커는 줄어듦)
    """
    if parallel_jobs <= 1 or len(jobs) == 1:
        results = []
        for i, job in enumerate(jobs, 1):
            print(f"\n{'='*50}")
            print(f"[{i}/{len(jobs)}] {job.rho_label}  (워커 {job.n_workers}개)")
            print(f"{'='*50}")
            results.append(run_full_simulation(job))
        return results

    print(f"\n병렬 배치: 동시 {parallel_jobs}개 시뮬 × 각 {jobs[0].n_workers}워커")
    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=parallel_jobs) as executor:
        future_map = {executor.submit(run_full_simulation, job): job for job in jobs}
        for future in as_completed(future_map):
            job = future_map[future]
            result = future.result()
            results.append(result)
            print(f"완료: {job.rho_label} → {result['run_id']}")
    return results
