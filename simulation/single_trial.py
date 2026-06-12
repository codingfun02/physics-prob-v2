"""1회 주사위 낙하 시뮬레이션."""

from __future__ import annotations

import numpy as np
import pybullet as p

from config import (
    ANG_VEL_THRESHOLD,
    DROP_HEIGHT,
    MAX_ANGULAR_VEL,
    MAX_SIM_STEPS,
    PHYSICS_DT,
    SETTLE_TIME,
    VEL_THRESHOLD,
)
from density.grid import RhoGrid
from physics.bodies import create_die, create_world
from physics.faces import get_top_face
from physics.inertia import InertiaProperties, compute_inertia


def _random_orientation() -> list[float]:
    """SO(3) 균일 분포 랜덤 자세 (단위 쿼터니언)."""
    q = np.random.randn(4)
    q /= np.linalg.norm(q)
    return q.tolist()


def _random_angular_velocity() -> list[float]:
    """각 축에 균일 랜덤 각속도."""
    w = np.random.uniform(-MAX_ANGULAR_VEL, MAX_ANGULAR_VEL, size=3)
    return w.tolist()


def run_single_trial(
    grid: RhoGrid,
    props: InertiaProperties | None = None,
    seed: int | None = None,
) -> int:
    """
    주사위 1회 던지기 → 위쪽 면 번호(1~6) 반환.

    과정: 높이 DROP_HEIGHT에서 랜덤 자세·각속도로 시작 → 낙하 → 바닥 충돌 → 정지.
    """
    if seed is not None:
        np.random.seed(seed)

    if props is None:
        props = compute_inertia(grid)

    p.connect(p.DIRECT)
    p.setTimeStep(PHYSICS_DT)
    create_world()
    die_id = create_die(grid, props)

    orn = _random_orientation()
    ang_vel = _random_angular_velocity()
    p.resetBasePositionAndOrientation(die_id, [0, 0, DROP_HEIGHT], orn)
    p.resetBaseVelocity(die_id, [0, 0, 0], ang_vel)

    settle_steps = int(SETTLE_TIME / PHYSICS_DT)
    still_count = 0

    for _ in range(MAX_SIM_STEPS):
        p.stepSimulation()
        lin_vel, ang_vel_now = p.getBaseVelocity(die_id)
        speed = np.linalg.norm(lin_vel)
        spin = np.linalg.norm(ang_vel_now)

        if speed < VEL_THRESHOLD and spin < ANG_VEL_THRESHOLD:
            still_count += 1
            if still_count >= settle_steps:
                break
        else:
            still_count = 0

    _, final_orn = p.getBasePositionAndOrientation(die_id)
    top_face = get_top_face(final_orn)
    p.disconnect()
    return top_face
