"""PyBullet GUI — 균일 주사위 1회 던지기 프로토타입 (버튼 클릭)."""

from __future__ import annotations

import time

import numpy as np
import pybullet as p

from config import (
    DROP_HEIGHT,
    MAX_SIM_STEPS,
    PHYSICS_DT,
    VEL_THRESHOLD,
    ANG_VEL_THRESHOLD,
    SETTLE_TIME,
)
from density.analytic import get_preset_rho
from physics.bodies import create_die, create_world
from physics.faces import get_bottom_face
from physics.inertia import compute_inertia
from simulation.single_trial import (
    reset_die_for_trial,
    trial_initial_conditions,
)

SLOW_FACTOR = 2.0
# PyBullet Params 패널은 ASCII만 표시됨 (한글 라벨 깨짐)
THROW_BTN_LABEL = "Throw (1x)"
THROW_KEY = ord("t")


def _configure_viewer() -> None:
    p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
    p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
    target_z = DROP_HEIGHT * 0.42
    cam_dist = max(6.0, DROP_HEIGHT * 1.25)
    p.resetDebugVisualizerCamera(
        cameraDistance=cam_dist,
        cameraYaw=45,
        cameraPitch=-22,
        cameraTargetPosition=[0, 0, target_z],
    )


def _is_settled(die_id: int) -> bool:
    lin_vel, ang_vel = p.getBaseVelocity(die_id)
    return (
        np.linalg.norm(lin_vel) < VEL_THRESHOLD
        and np.linalg.norm(ang_vel) < ANG_VEL_THRESHOLD
    )


def main() -> None:
    grid = get_preset_rho("uniform")
    props = compute_inertia(grid)

    p.connect(p.GUI)
    p.setRealTimeSimulation(0)
    p.setTimeStep(PHYSICS_DT)
    p.setGravity(0, 0, -9.81)
    _configure_viewer()

    create_world()
    die_id = create_die(grid, props)
    p.changeVisualShape(die_id, -1, rgbaColor=[0.75, 0.78, 0.85, 1.0])

    throw_btn = p.addUserDebugParameter(THROW_BTN_LABEL, 1, 0, 0)

    last_btn_val = 0
    throw_count = 0
    simulating = False
    still_count = 0
    settle_steps = int(SETTLE_TIME / PHYSICS_DT)
    step_count = 0

    def _start_throw() -> None:
        nonlocal simulating, still_count, step_count, orn, ang_vel
        if simulating:
            return
        orn, ang_vel = trial_initial_conditions()
        reset_die_for_trial(die_id, orn, ang_vel)
        simulating = True
        still_count = 0
        step_count = 0
        print(f"\n--- 던지기 #{throw_count + 1} ---")

    orn, ang_vel = trial_initial_conditions()
    reset_die_for_trial(die_id, orn, ang_vel)

    print("PyBullet GUI 프로토타입 — 창을 닫으면 종료됩니다.")
    print(f"우측 Params 패널 '{THROW_BTN_LABEL}' 버튼 또는 키 T 로 던집니다.")

    try:
        while p.isConnected():
            btn_val = int(p.readUserDebugParameter(throw_btn))
            if not simulating and btn_val != last_btn_val:
                _start_throw()
            last_btn_val = btn_val

            keys = p.getKeyboardEvents()
            if (
                not simulating
                and THROW_KEY in keys
                and keys[THROW_KEY] & p.KEY_WAS_TRIGGERED
            ):
                _start_throw()

            if simulating:
                p.stepSimulation()
                step_count += 1

                if _is_settled(die_id):
                    still_count += 1
                    if still_count >= settle_steps:
                        _, final_orn = p.getBasePositionAndOrientation(die_id)
                        bottom = get_bottom_face(final_orn)
                        throw_count += 1
                        simulating = False
                        print(f"바닥의 눈: {bottom}  (총 {throw_count}회)")
                else:
                    still_count = 0

                if step_count >= MAX_SIM_STEPS:
                    _, final_orn = p.getBasePositionAndOrientation(die_id)
                    bottom = get_bottom_face(final_orn)
                    throw_count += 1
                    simulating = False
                    print(f"시간 초과 — 바닥의 눈: {bottom}  (총 {throw_count}회)")

                time.sleep(PHYSICS_DT * SLOW_FACTOR)
            else:
                time.sleep(1.0 / 60.0)

    except p.error:
        pass
    finally:
        print(f"\n종료 — 총 {throw_count}회 던짐")


if __name__ == "__main__":
    main()
