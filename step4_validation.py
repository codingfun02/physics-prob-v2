"""4단계 검증: 균일 밀도에서 6면 확률이 1/6 근처인지 확인."""

import numpy as np

from density.analytic import get_preset_rho
from simulation.monte_carlo import run_monte_carlo

N = 2000
EXPECTED = 1 / 6
MAX_SIGMA = 4.0


def main():
    print(f"=== 4단계 검증 (uniform, N={N}) ===")
    grid = get_preset_rho("uniform")
    probs, _ = run_monte_carlo(grid, n_trials=N, n_workers=2)

    all_ok = True
    for face in range(1, 7):
        p = probs[face]
        se = np.sqrt(p * (1 - p) / N)
        diff = abs(p - EXPECTED)
        ok = diff <= MAX_SIGMA * se
        status = "OK" if ok else "FAIL"
        print(f"  눈 {face}: {p:.4f}  (차이 {diff:.4f}, 허용 {MAX_SIGMA*se:.4f})  [{status}]")
        all_ok = all_ok and ok

    if all_ok:
        print("\n검증 통과: 균일 밀도 → 각 면 약 1/6")
    else:
        print("\n검증 실패: 파라미터 조정 또는 N 증가 필요")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
