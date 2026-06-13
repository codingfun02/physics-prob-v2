"""7개 시뮬 결과 통계 분석 (일회성)."""

import json
import math
from pathlib import Path

from density.analytic import SPHERE_STUDY_SPECS, get_preset_rho
from physics.inertia import compute_inertia

N0 = 1 / 6
history = json.loads(Path("output/history.json").read_text(encoding="utf-8"))
runs = history["runs"]
se = math.sqrt(N0 * (1 - N0) / 50000)  # ~0.00167

print("=== 7개 시뮬 (N=50000, 기대값 1/6=16.67%) ===\n")
print(f"{'rho':22s}  p(2)   p(5)   최다눈  최다%   Δp2    z2    Δp5    z5")
print("-" * 78)
for r in runs:
    p = {int(k): float(v) for k, v in r["probabilities"].items()}
    top = max(p, key=p.get)
    z2 = (p[2] - N0) / se
    z5 = (p[5] - N0) / se
    print(
        f"{r['rho_name']:22s}  {p[2]:.4f} {p[5]:.4f}   {top}    {p[top]:.4f}  "
        f"{p[2]-N0:+.4f} {z2:+.2f}  {p[5]-N0:+.4f} {z5:+.2f}"
    )

print("\n=== 가설: +x 밀도(중심 0.15,0,0) -> 바닥에 눈 2(+x면) 유리 ===\n")
for r in runs:
    name = r["rho_name"]
    if name == "uniform":
        continue
    p2 = float(r["probabilities"]["2"])
    z2 = (p2 - N0) / se
    if z2 > 1.96:
        verdict = "통계적 지지 (p<0.05)"
    elif z2 > 0:
        verdict = "방향만 일치, 비유의"
    else:
        verdict = "가설과 반대"
    print(f"  {name:20s}  p2={p2:.4f}  z2={z2:+.2f}  -> {verdict}")

print("\n=== 배율 증가에 따른 p(2) 변화 (단조 증가해야 가설 강화) ===\n")
for radius in (0.2, 0.3):
    print(f"  r={radius}:")
    for spec in SPHERE_STUDY_SPECS:
        if spec["radius"] != radius:
            continue
        r = next(x for x in runs if x["rho_name"] == spec["name"])
        p2 = float(r["probabilities"]["2"])
        print(f"    f={spec['factor']}  p2={p2:.4f} ({(p2-N0)*100:+.2f}%p)")

print("\n=== chi-square: 6면이 균일한가? (5 dof, 11.07 이상이면 p<0.05) ===\n")
for r in runs:
    obs = [int(r["counts"][str(i)]) for i in range(1, 7)]
    n = sum(obs)
    exp = n / 6
    chi2 = sum((o - exp) ** 2 / exp for o in obs)
    sig = "유의" if chi2 > 11.07 else "비유의"
    print(f"  {r['rho_name']:22s}  chi2={chi2:2.2f}  {sig}")

print("\n=== 물리량 (COM_x, 관성 비대칭) ===\n")
uniform = compute_inertia(get_preset_rho("uniform"))
for spec in SPHERE_STUDY_SPECS:
    ip = compute_inertia(get_preset_rho(spec["name"]))
    I = ip.principal_moments
    asym = (I.max() - I.min()) / I.mean() * 100
    r = next(x for x in runs if x["rho_name"] == spec["name"])
    p2 = float(r["probabilities"]["2"])
    print(
        f"  {spec['name']:18s}  COM_x={ip.com[0]:.5f}  "
        f"비대칭={asym:.3f}%  p2={p2:.4f}"
    )

# minimum detectable effect at 50000 trials
z_detect = 1.96
mde = z_detect * se
print(f"\n=== 검출 한계 (N=50000, 양측 5%) ===")
print(f"  표준오차 SE ≈ {se*100:.3f}%p")
print(f"  검출 가능한 최소 편차 ≈ {mde*100:.2f}%p (|z|>1.96)")
