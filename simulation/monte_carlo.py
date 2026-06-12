"""몬테카를로 시뮬레이션 — N회 반복 후 면별 확률."""

from __future__ import annotations

from multiprocessing import Pool, cpu_count
from pathlib import Path

from density.grid import RhoGrid
from physics.inertia import compute_inertia
from simulation.progress import MonteCarloProgress
from simulation.results import save_checkpoint
from simulation.single_trial import run_single_trial

# 워커 프로세스가 공유할 격자 (초기화 시 설정)
_worker_grid: RhoGrid | None = None
_worker_props = None


def _init_worker(grid: RhoGrid):
    global _worker_grid, _worker_props
    _worker_grid = grid
    _worker_props = compute_inertia(grid)


def _run_one_trial(_: int) -> int:
    assert _worker_grid is not None
    return run_single_trial(_worker_grid, props=_worker_props)


def run_monte_carlo(
    grid: RhoGrid,
    n_trials: int = 50_000,
    n_workers: int | None = None,
    checkpoint_path: str | Path | None = None,
    checkpoint_interval: int = 1000,
    rho_name: str = "unknown",
) -> tuple[dict[int, float], dict[int, int]]:
    """
    N회 시행 후 (확률 dict, 횟수 dict) 반환.

    checkpoint_path가 있으면 checkpoint_interval마다 중간 결과를 JSON으로 저장.
    """
    if n_workers is None:
        n_workers = max(1, cpu_count() - 1)

    counts = {i: 0 for i in range(1, 7)}
    completed = 0

    with Pool(processes=n_workers, initializer=_init_worker, initargs=(grid,)) as pool:
        iterator = pool.imap(_run_one_trial, range(n_trials), chunksize=50)
        with MonteCarloProgress(n_trials, desc="시뮬레이션") as progress:
            for face in iterator:
                counts[face] += 1
                completed += 1
                progress.update(1)
                if (
                    checkpoint_path is not None
                    and checkpoint_interval > 0
                    and completed % checkpoint_interval == 0
                ):
                    save_checkpoint(
                        checkpoint_path,
                        counts=counts,
                        completed=completed,
                        n_trials=n_trials,
                        rho_name=rho_name,
                    )

    probs = {face: counts[face] / n_trials for face in counts}
    return probs, counts
