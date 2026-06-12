"""몬테카를로 시뮬레이션 — N회 반복 후 면별 확률."""

from __future__ import annotations

from multiprocessing import Pool, cpu_count

import numpy as np
from tqdm import tqdm

from density.grid import RhoGrid
from physics.inertia import compute_inertia
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
) -> dict[int, float]:
    """
    N회 시행 후 면별 확률 dict {1: p1, 2: p2, ...} 반환.
    """
    if n_workers is None:
        n_workers = max(1, cpu_count() - 1)

    counts = {i: 0 for i in range(1, 7)}

    with Pool(processes=n_workers, initializer=_init_worker, initargs=(grid,)) as pool:
        results = list(
            tqdm(
                pool.imap(_run_one_trial, range(n_trials), chunksize=50),
                total=n_trials,
                desc="시뮬레이션",
            )
        )

    for face in results:
        counts[face] += 1

    return {face: count / n_trials for face, count in counts.items()}
