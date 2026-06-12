"""3단계 테스트: PyBullet 1회 낙하."""

from density.analytic import get_preset_rho
from simulation.single_trial import run_single_trial

grid = get_preset_rho("uniform")
face = run_single_trial(grid, seed=42)
print(f"=== 3단계 결과 ===")
print(f"1회 시험 — 위쪽 면: {face}")
