"""몬테카를로 시뮬레이션 — N회 반복 후 면별 확률."""

from __future__ import annotations

from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from pathlib import Path

from density.grid import RhoGrid
from physics.inertia import compute_inertia
from simulation.cancel import is_cancel_requested
from simulation.progress import MonteCarloProgress
from simulation.results import counts_to_probs, save_checkpoint
from simulation.single_trial import run_single_trial

# 워커 프로세스가 공유할 격자 (초기화 시 설정)
_worker_grid: RhoGrid | None = None
_worker_props = None


@dataclass
class MonteCarloResult:
    probs: dict[int, float]
    counts: dict[int, int]
    completed: int
    target_trials: int
    cancelled: bool

    def __iter__(self):
        yield self.probs
        yield self.counts


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
) -> MonteCarloResult:
    """
    N회 시행 후 결과 반환.

    Ctrl+C(중단 요청) 시 완료된 시행까지 저장하고 cancelled=True로 반환.
    """
    if n_workers is None:
        n_workers = max(1, cpu_count() - 1)

    counts = {i: 0 for i in range(1, 7)}
    completed = 0
    cancelled = False
    pool: Pool | None = None

    try:
        pool = Pool(processes=n_workers, initializer=_init_worker, initargs=(grid,))
        iterator = pool.imap(_run_one_trial, range(n_trials), chunksize=50)
        with MonteCarloProgress(n_trials, desc="시뮬레이션") as progress:
            for face in iterator:
                if is_cancel_requested():
                    cancelled = True
                    break
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
    finally:
        if pool is not None:
            if cancelled:
                pool.terminate()
            else:
                pool.close()
            pool.join()

    if cancelled and completed > 0 and checkpoint_path is not None:
        save_checkpoint(
            checkpoint_path,
            counts=counts,
            completed=completed,
            n_trials=n_trials,
            rho_name=rho_name,
        )

    if completed == 0:
        probs = {face: 0.0 for face in counts}
    else:
        probs = counts_to_probs(counts, completed)

    return MonteCarloResult(
        probs=probs,
        counts=counts,
        completed=completed,
        target_trials=n_trials,
        cancelled=cancelled,
    )
