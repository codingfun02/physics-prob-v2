"""누적된 시뮬레이션 기록 목록 보기."""

from simulation.results import load_history
from config import OUTPUT_DIR

history = load_history(OUTPUT_DIR)
runs = history.get("runs", [])

print(f"=== 시뮬레이션 기록 ({len(runs)}회) ===\n")
if not runs:
    print("아직 기록이 없습니다. main.py로 시뮬레이션을 실행하세요.")
else:
    for i, run in enumerate(runs, 1):
        probs = run.get("probabilities", {})
        top = max(probs, key=probs.get) if probs else "?"
        print(f"[{i}] {run['run_id']}")
        print(f"    시각: {run['timestamp']}")
        print(f"    ρ={run['rho_name']}, N={run['n_trials']}")
        print(f"    최다 바닥의 눈: {top} ({probs.get(top, 0):.2%})")
        print(f"    JSON: {run['paths']['results_json']}")
        print()
