"""2단계 테스트: 관성 계산 (균일 밀도 → COM≈0, I≈M/12)."""

import numpy as np

from density.analytic import get_preset_rho
from physics.inertia import compute_inertia

grid = get_preset_rho("uniform")
props = compute_inertia(grid)

print("=== 2단계 결과 ===")
print(f"총 질량 M = {props.mass:.4f} kg  (rho=1, 부피=1m³ 이면 1kg)")
print(f"질량중심   = {props.com}")
print(f"관성텐서 대각 = {np.diag(props.inertia_tensor)}")
print(f"이론값 M/12  = {props.mass / 12:.6f}  (균일 정육면체)")
