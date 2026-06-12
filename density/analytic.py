"""연속 함수 ρ(x,y,z) → 6×6×6 격자로 변환."""

from __future__ import annotations

from typing import Callable

import numpy as np

from config import DIE_HALF_SIZE, GRID_N
from .grid import RhoGrid

RhoFunc = Callable[[float, float, float], float]


def discretize_rho(
    func: RhoFunc,
    n: int = GRID_N,
    half_size: float = DIE_HALF_SIZE,
) -> RhoGrid:
    """
    해석적 밀도 함수를 n×n×n 격자로 샘플링합니다.

    각 소셀 중심 좌표에서 func(x,y,z) 값을 읽어 그 칸의 밀도로 씁니다.
  """
    cell_size = (2 * half_size) / n
    axis = np.linspace(
        -half_size + cell_size / 2,
        half_size - cell_size / 2,
        n,
    )
    rho = np.zeros((n, n, n))
    for i, x in enumerate(axis):
        for j, y in enumerate(axis):
            for k, z in enumerate(axis):
                rho[i, j, k] = func(x, y, z)
    return RhoGrid(rho, n=n, half_size=half_size)


def rho_uniform(x: float, y: float, z: float) -> float:
    """모든 위치에서 밀도 = 1 (공정한 주사위)."""
    return 1.0


def rho_linear_x(x: float, y: float, z: float, alpha: float = 2.0) -> float:
    """+x 방향으로 갈수록 무거움."""
    return max(0.0, 1.0 + alpha * x)


def rho_layer(x: float, y: float, z: float, alpha: float = 2.0) -> float:
    """+z(위) 방향으로 갈수록 무거움."""
    return max(0.0, 1.0 + alpha * z)


def rho_corner_heavy(
    x: float,
    y: float,
    z: float,
    x0: float = 0.4,
    y0: float = 0.4,
    z0: float = 0.4,
    amplitude: float = 10.0,
    sigma: float = 0.15,
) -> float:
    """한 꼭짓점 근처에 질량이 몰림 (가우시안 덩어리)."""
    r2 = (x - x0) ** 2 + (y - y0) ** 2 + (z - z0) ** 2
    return 1.0 + amplitude * np.exp(-r2 / (2 * sigma**2))


PRESETS: dict[str, dict] = {
    "uniform": {"func": rho_uniform, "params": {}},
    "linear_x": {"func": rho_linear_x, "params": {"alpha": 2.0}},
    "layer": {"func": rho_layer, "params": {"alpha": 2.0}},
    "corner_heavy": {"func": rho_corner_heavy, "params": {}},
}


def get_preset_rho(name: str, **override_params) -> RhoGrid:
    """이름으로 프리셋 밀도 격자를 만듭니다. 예: get_preset_rho('uniform')"""
    if name not in PRESETS:
        raise ValueError(f"Unknown preset '{name}'. Choose from {list(PRESETS)}")
    entry = PRESETS[name]
    func = entry["func"]
    params = {**entry["params"], **override_params}

    def wrapped(x, y, z):
        return func(x, y, z, **params)

    return discretize_rho(wrapped)
