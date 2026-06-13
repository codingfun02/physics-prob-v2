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


def rho_sphere_bump(
    x: float,
    y: float,
    z: float,
    x0: float = 0.1,
    y0: float = 0.0,
    z0: float = 0.0,
    radius: float = 0.2,
    factor: float = 1.5,
) -> float:
    """구 내부(중심 x0,y0,z0, 반지름 radius)에서만 밀도를 factor배."""
    r2 = (x - x0) ** 2 + (y - y0) ** 2 + (z - z0) ** 2
    if r2 <= radius**2:
        return factor
    return 1.0


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
    "sphere_bump": {
        "func": rho_sphere_bump,
        "params": {"x0": 0.1, "y0": 0.0, "z0": 0.0, "radius": 0.2, "factor": 1.5},
    },
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


# --- 구 밀도 실험 (레거시 7종) ---

def _register_sphere_preset(
    name: str,
    x0: float,
    y0: float,
    z0: float,
    radius: float,
    factor: float,
) -> None:
    from density.sphere_constraints import assert_sphere_inside_cube

    assert_sphere_inside_cube(x0, y0, z0, radius, label=name)
    PRESETS[name] = {
        "func": rho_sphere_bump,
        "params": {"x0": x0, "y0": y0, "z0": z0, "radius": radius, "factor": factor},
    }


SPHERE_STUDY_SPECS: list[dict] = [
    {"name": "sphere_r02_f13", "x0": 0.15, "radius": 0.2, "factor": 1.3},
    {"name": "sphere_r02_f16", "x0": 0.15, "radius": 0.2, "factor": 1.6},
    {"name": "sphere_r02_f19", "x0": 0.15, "radius": 0.2, "factor": 1.9},
    {"name": "sphere_r03_f13", "x0": 0.15, "radius": 0.3, "factor": 1.3},
    {"name": "sphere_r03_f16", "x0": 0.15, "radius": 0.3, "factor": 1.6},
    {"name": "sphere_r03_f19", "x0": 0.15, "radius": 0.3, "factor": 1.9},
]
for _spec in SPHERE_STUDY_SPECS:
    _register_sphere_preset(
        _spec["name"],
        x0=_spec["x0"],
        y0=0.0,
        z0=0.0,
        radius=_spec["radius"],
        factor=_spec["factor"],
    )

SPHERE_STUDY_NAMES = [s["name"] for s in SPHERE_STUDY_SPECS]
SPHERE_STUDY_SIM_NAMES: list[str] = ["uniform"] + SPHERE_STUDY_NAMES


# --- 변인 통제 실험 v2 (50k 분석 기반 강화) ---
# 50k 결과: 배율↑ → |Δp|↑ (f2.5에서 ~0.9%p), 중심↑ → p(2)↑, r=0.14는 효과 미미
# v2: GRID_N=12, +x 쪽으로 중심 이동, 배율·반지름 확대, MAX_ANGULAR_VEL↓

CONTROLLED_STUDY_SPECS: list[dict] = [
    # A: 배율 (x0=0.28, r=0.20 고정)
    {"name": "ctrl_factor_f30", "group": "factor", "x0": 0.28, "radius": 0.20, "factor": 3.0},
    {"name": "ctrl_factor_f40", "group": "factor", "x0": 0.28, "radius": 0.20, "factor": 4.0},
    {"name": "ctrl_factor_f50", "group": "factor", "x0": 0.28, "radius": 0.20, "factor": 5.0},
    # B: 반지름 (x0=0.28, factor=4.0 고정)
    {"name": "ctrl_radius_r16", "group": "radius", "x0": 0.28, "radius": 0.16, "factor": 4.0},
    {"name": "ctrl_radius_r20", "group": "radius", "x0": 0.28, "radius": 0.20, "factor": 4.0},
    {"name": "ctrl_radius_r22", "group": "radius", "x0": 0.28, "radius": 0.22, "factor": 4.0},
    # C: 중심 (r=0.18, factor=4.0 고정)
    {"name": "ctrl_center_x22", "group": "center", "x0": 0.22, "radius": 0.18, "factor": 4.0},
    {"name": "ctrl_center_x28", "group": "center", "x0": 0.28, "radius": 0.18, "factor": 4.0},
    {"name": "ctrl_center_x32", "group": "center", "x0": 0.32, "radius": 0.18, "factor": 4.0},
]
for _spec in CONTROLLED_STUDY_SPECS:
    _register_sphere_preset(
        _spec["name"],
        x0=_spec["x0"],
        y0=0.0,
        z0=0.0,
        radius=_spec["radius"],
        factor=_spec["factor"],
    )

CONTROLLED_STUDY_NAMES = [s["name"] for s in CONTROLLED_STUDY_SPECS]
CONTROLLED_STUDY_SIM_NAMES: list[str] = ["uniform"] + CONTROLLED_STUDY_NAMES


# --- 1단계: ρ 전이 스캔 (x0=0.28, r=0.20 고정) ---
RHO_SCAN_SPECS: list[dict] = [
    {"name": "ctrl_factor_f20", "group": "factor", "x0": 0.28, "radius": 0.20, "factor": 2.0},
    {"name": "ctrl_factor_f25", "group": "factor", "x0": 0.28, "radius": 0.20, "factor": 2.5},
    {"name": "ctrl_factor_f35", "group": "factor", "x0": 0.28, "radius": 0.20, "factor": 3.5},
    {"name": "ctrl_factor_f60", "group": "factor", "x0": 0.28, "radius": 0.20, "factor": 6.0},
]
for _spec in RHO_SCAN_SPECS:
    if _spec["name"] not in PRESETS:
        _register_sphere_preset(
            _spec["name"],
            x0=_spec["x0"],
            y0=0.0,
            z0=0.0,
            radius=_spec["radius"],
            factor=_spec["factor"],
        )

# f30·f40·f50은 CONTROLLED_STUDY에 이미 등록됨
RHO_SCAN_SIM_NAMES: list[str] = [
    "ctrl_factor_f20",
    "ctrl_factor_f25",
    "ctrl_factor_f30",
    "ctrl_factor_f35",
    "ctrl_factor_f40",
    "ctrl_factor_f50",
    "ctrl_factor_f60",
]

ALL_CONTROLLED_SPECS: list[dict] = CONTROLLED_STUDY_SPECS + RHO_SCAN_SPECS


def lookup_controlled_spec(preset_name: str) -> dict | None:
    for spec in ALL_CONTROLLED_SPECS:
        if spec["name"] == preset_name:
            return spec
    return None


def print_rho_scan_plan() -> None:
    from config import GRID_N, MAX_ANGULAR_VEL, RESTITUTION

    print("=== 1단계 — ρ 스캔 (전이 구간) ===")
    print(f"  GRID_N={GRID_N}, MAX_ANGULAR_VEL={MAX_ANGULAR_VEL}, RESTITUTION={RESTITUTION}")
    print("  고정: 편심x좌표=0.28, 반지름=0.2")
    print("  목적: ρ=3↔4 사이 p(2)→p(5) 전환점 확인\n")
    for name in RHO_SCAN_SIM_NAMES:
        spec = lookup_controlled_spec(name)
        if spec:
            print(f"    {name}: ρ={spec['factor']:g}")
    print()


def controlled_study_title(spec: dict) -> str:
    g = spec["group"]
    if g == "factor":
        return f"배율 f={spec['factor']} (x0={spec['x0']}, r={spec['radius']})"
    if g == "radius":
        return f"반지름 r={spec['radius']} (x0={spec['x0']}, f={spec['factor']})"
    return f"중심 x0={spec['x0']} (r={spec['radius']}, f={spec['factor']})"


def print_controlled_study_plan() -> None:
    from config import GRID_N, MAX_ANGULAR_VEL, RESTITUTION

    print("=== 변인 통제 실험 v2 (강화 파라미터) ===")
    print(f"  GRID_N={GRID_N}, MAX_ANGULAR_VEL={MAX_ANGULAR_VEL}, RESTITUTION={RESTITUTION}")
    print("  가설: +x 고밀도 → 바닥의 눈 2(+x면) 또는 반대 5(-x면) 편향")
    print("  50k 분석: 배율·+x 중심이 신호가 가장 뚜렷 → v2에서 강화\n")
    groups = {"factor": "A 배율", "radius": "B 반지름", "center": "C 중심"}
    for gkey, glabel in groups.items():
        print(f"  [{glabel}]")
        for s in CONTROLLED_STUDY_SPECS:
            if s["group"] == gkey:
                print(f"    {s['name']}: {controlled_study_title(s)}")
        print()


def sphere_study_title(index: int, preset_name: str | None = None) -> str:
    if preset_name is None:
        preset_name = SPHERE_STUDY_SIM_NAMES[index - 1]
    if preset_name == "uniform":
        return f"{index}. 균일 밀도 (ρ=1, 기준)"
    ctrl = lookup_controlled_spec(preset_name)
    if ctrl:
        return f"{index}. {controlled_study_title(ctrl)}"
    sph = next((s for s in SPHERE_STUDY_SPECS if s["name"] == preset_name), None)
    if sph:
        return (
            f"{index}. 구 r={sph['radius']}, f={sph['factor']} "
            f"(x0={sph['x0']})"
        )
    return f"{index}. {preset_name}"
