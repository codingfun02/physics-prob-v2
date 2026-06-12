"""여러 밀도 프리셋 시뮬레이션 — 순차 또는 병렬."""

from __future__ import annotations

import argparse
import time
from multiprocessing import cpu_count

from density.analytic import PRESETS
from simulation.batch import allocate_workers, build_jobs, run_batch


def main():
    parser = argparse.ArgumentParser(
        description="여러 ρ 설정을 한 번에 시뮬레이션 (순차/병렬)"
    )
    parser.add_argument(
        "--rhos",
        type=str,
        default="uniform,linear_x,layer,sphere_bump,corner_heavy",
        help="쉼표로 구분한 프리셋 목록",
    )
    parser.add_argument("--all-presets", action="store_true", help="PRESETS 전부 실행")
    parser.add_argument("--trials", type=int, default=50000)
    parser.add_argument(
        "--parallel",
        type=int,
        default=None,
        help="동시 실행할 시뮬 개수 (미지정=자동). 1이면 순차",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="전체 CPU에 쓸 워커 합 (기본: 코어수-1)",
    )
    parser.add_argument("--alpha", type=float, default=None)
    parser.add_argument("--checkpoint-interval", type=int, default=5000)
    args = parser.parse_args()

    if args.all_presets:
        rho_names = list(PRESETS.keys())
    else:
        rho_names = [s.strip() for s in args.rhos.split(",") if s.strip()]

    n_sims = len(rho_names)
    parallel_jobs, workers_per_sim = allocate_workers(
        n_sims,
        parallel_jobs=args.parallel,
        total_workers=args.workers,
    )

    print("=== 배치 시뮬레이션 계획 ===")
    print(f"  CPU 코어:     {cpu_count()}")
    print(f"  시뮬 개수:    {n_sims}")
    print(f"  시행/시뮬:    {args.trials}")
    print(f"  동시 실행:    {parallel_jobs}개")
    print(f"  시뮬당 워커:  {workers_per_sim}개")
    print(f"  대상:         {', '.join(rho_names)}")
    if parallel_jobs == 1:
        print("\n  → 순차 실행: 시뮬당 CPU를 최대한 씁니다 (보통 가장 효율적).")
    else:
        print(
            f"\n  → 병렬 실행: {parallel_jobs}개를 동시에 돌립니다. "
            "전체 시간은 줄지만 시뮬당은 느려질 수 있습니다."
        )

    jobs = build_jobs(
        rho_names,
        n_trials=args.trials,
        workers_per_sim=workers_per_sim,
        alpha=args.alpha,
        checkpoint_interval=args.checkpoint_interval,
    )

    t0 = time.perf_counter()
    results = run_batch(jobs, parallel_jobs=parallel_jobs)
    elapsed = time.perf_counter() - t0

    print(f"\n{'='*50}")
    print(f"배치 완료 — 총 {elapsed/60:.1f}분, {len(results)}개 시뮬")
    print(f"{'='*50}")
    for r in sorted(results, key=lambda x: x["rho_label"]):
        top = max(r["probabilities"], key=r["probabilities"].get)
        p = r["probabilities"][top]
        print(f"  {r['rho_label']:25s}  바닥의 눈 {top} 최다 ({p:.1%})  → {r['run_id']}")
    print(f"\n전체 기록: output/history.json")


if __name__ == "__main__":
    main()
