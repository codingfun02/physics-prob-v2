"""구 밀도 덩어리가 주사위 정육면체 안에 들어가는지 검증."""

from __future__ import annotations

from config import DIE_HALF_SIZE


def max_inscribed_sphere_radius(
    x0: float,
    y0: float = 0.0,
    z0: float = 0.0,
    half: float = DIE_HALF_SIZE,
) -> float:
    """
    중심 (x0,y0,z0)에서 정육면체 [-half,half]³ 안에 넣을 수 있는 구의 최대 반지름.

    각 축에서 x0±r, y0±r, z0±r 가 모두 [-half, half] 안에 있어야 함.
    """
    return min(
        x0 + half,
        half - x0,
        y0 + half,
        half - y0,
        z0 + half,
        half - z0,
    )


def sphere_fits_in_cube(
    x0: float,
    y0: float,
    z0: float,
    radius: float,
    half: float = DIE_HALF_SIZE,
) -> bool:
    return (
        radius <= max_inscribed_sphere_radius(x0, y0, z0, half) + 1e-12
        and radius > 0
    )


def assert_sphere_inside_cube(
    x0: float,
    y0: float,
    z0: float,
    radius: float,
    half: float = DIE_HALF_SIZE,
    label: str = "",
) -> None:
    """구가 정육면체 밖으로 나가면 ValueError."""
    r_max = max_inscribed_sphere_radius(x0, y0, z0, half)
    if radius > r_max + 1e-9:
        tag = f" ({label})" if label else ""
        raise ValueError(
            f"구가 주사위 밖으로 나갑니다{tag}: "
            f"중심=({x0},{y0},{z0}), r={radius}, "
            f"허용 최대 r={r_max:.4f} (정육면체 ±{half})"
        )
