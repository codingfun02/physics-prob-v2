"""격자 밀도 → 질량, 질량중심, 관성텐서 계산."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial.transform import Rotation
from scipy.linalg import eigh

from density.grid import RhoGrid


@dataclass
class InertiaProperties:
    """PyBullet에 넣을 강체 물성."""

    mass: float
    com: np.ndarray              # 질량중심 (주사위 좌표계)
    inertia_tensor: np.ndarray   # 3×3 관성텐서 (원점 기준 → COM 기준으로 변환됨)
    principal_moments: np.ndarray  # 주관성 모멘트 [I1, I2, I3]
    principal_rotation: Rotation   # 주축 방향 (body → principal)


def compute_inertia(grid: RhoGrid) -> InertiaProperties:
    """
    6×6×6 격자에서 강체의 질량·질량중심·관성텐서를 계산합니다.

    각 소셀을 작은 점질량으로 보고 합산합니다.
    """
    centers = grid.cell_centers.reshape(-1, 3)
    masses = (grid.rho * grid.cell_volume).reshape(-1)
    total_mass = float(np.sum(masses))
    if total_mass <= 0:
        raise ValueError("총 질량이 0입니다.")

    com = np.sum(masses[:, np.newaxis] * centers, axis=0) / total_mass

    # COM 기준 관성텐서
    I = np.zeros((3, 3))
    for m, r in zip(masses, centers):
        dr = r - com
        x, y, z = dr
        I[0, 0] += m * (y * y + z * z)
        I[1, 1] += m * (x * x + z * z)
        I[2, 2] += m * (x * x + y * y)
        I[0, 1] -= m * x * y
        I[0, 2] -= m * x * z
        I[1, 2] -= m * y * z
    I[1, 0] = I[0, 1]
    I[2, 0] = I[0, 2]
    I[2, 1] = I[1, 2]

    # 고유값 분해 → 주관성 축
    eigvals, eigvecs = eigh(I)
    order = np.argsort(eigvals)
    principal_moments = eigvals[order]
    principal_axes = eigvecs[:, order]

    # I₁≈I₂≈I₃ (균일·구 대칭): 주축이 유일하지 않음 → body x,y,z 고정
    i_mean = float(np.mean(principal_moments))
    if i_mean > 0:
        rel_spread = float(
            (principal_moments.max() - principal_moments.min()) / i_mean
        )
        if rel_spread < 1e-8:
            principal_axes = np.eye(3)
            principal_moments = np.diag(I)

    # det=-1 이면 반사 행렬 → 한 축 뒤집어서 올바른 회전행렬로
    if np.linalg.det(principal_axes) < 0:
        principal_axes[:, 0] *= -1

    rot = Rotation.from_matrix(principal_axes)

    return InertiaProperties(
        mass=total_mass,
        com=com,
        inertia_tensor=I,
        principal_moments=principal_moments,
        principal_rotation=rot,
    )
