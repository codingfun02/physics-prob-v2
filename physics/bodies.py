"""PyBullet 바닥·주사위 body 생성."""

from __future__ import annotations

import pybullet as p

from config import DIE_HALF_SIZE, FRICTION, RESTITUTION
from density.grid import RhoGrid
from physics.inertia import InertiaProperties, compute_inertia


def create_world() -> int:
    """바닥(평면)이 있는 물리 세계를 만들고 body id를 반환하지 않음."""
    p.setGravity(0, 0, -9.81)

    plane_shape = p.createCollisionShape(p.GEOM_PLANE)
    p.createMultiBody(0, plane_shape)
    p.changeDynamics(0, -1, lateralFriction=FRICTION, restitution=RESTITUTION)
    return 0


def create_die(grid: RhoGrid, props: InertiaProperties | None = None) -> int:
    """비균일 밀도 주사위를 하나의 강체 상자로 생성합니다."""
    if props is None:
        props = compute_inertia(grid)

    half = DIE_HALF_SIZE
    col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[half, half, half])

    principal_quat = props.principal_rotation.as_quat().tolist()  # [x,y,z,w]

    die_id = p.createMultiBody(
        baseMass=props.mass,
        baseCollisionShapeIndex=col,
        basePosition=[0, 0, 0],
        baseOrientation=[0, 0, 0, 1],
        baseInertialFramePosition=props.com.tolist(),
        baseInertialFrameOrientation=principal_quat,
    )

    p.changeDynamics(
        die_id,
        -1,
        lateralFriction=FRICTION,
        restitution=RESTITUTION,
        localInertiaDiagonal=props.principal_moments.tolist(),
    )
    return die_id
