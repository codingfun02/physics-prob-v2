"""주사위 자세 → 위쪽(+z) 면 번호 판정."""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation

from config import FACE_LABELS


def get_top_face(orientation_xyzw: list | np.ndarray) -> int:
    """
    PyBullet 쿼터니언 [x,y,z,w]을 받아 위쪽(+z)에 오는 면 번호를 반환합니다.

    원리: 각 면의 '바깥 방향' 벡터를 회전시킨 뒤,
          월드 +z축과 가장 평행한 면이 '위쪽 면'입니다.
    """
    q = np.asarray(orientation_xyzw)
    rot = Rotation.from_quat(q)  # scipy: [x,y,z,w]

    best_label = 1
    best_dot = -2.0
    up = np.array([0.0, 0.0, 1.0])

    for normal, label in FACE_LABELS.items():
        world_normal = rot.apply(np.array(normal, dtype=float))
        dot = float(np.dot(world_normal, up))
        if dot > best_dot:
            best_dot = dot
            best_label = label

    return best_label
