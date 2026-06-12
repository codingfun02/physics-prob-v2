"""시뮬레이션 전역 설정 — 나중에 여기 숫자만 바꿔도 됩니다."""

# 주사위 크기: 한 변 1m, 중심이 원점 (0,0,0)
DIE_HALF_SIZE = 0.5  # 반쪽 길이 → 전체 [-0.5, 0.5]

# 밀도 격자 해상도 (6×6×6 = 216칸)
GRID_N = 6

# 낙하 조건
DROP_HEIGHT = 1.5       # 주사위 중심이 바닥 위 몇 m에서 시작할지
MAX_ANGULAR_VEL = 5.0   # 초기 각속도 최대값 (rad/s)

# 바닥 물성
FRICTION = 0.5
RESTITUTION = 0.3  # 반발계수 (0=튕김 없음, 1=완전 탄성)

# 정지 판정
VEL_THRESHOLD = 0.01       # m/s
ANG_VEL_THRESHOLD = 0.05   # rad/s
SETTLE_TIME = 0.1          # 초 (이 시간 동안 느리면 "멈춤")

# PyBullet
PHYSICS_DT = 1.0 / 240.0
MAX_SIM_STEPS = 2400  # 최대 10초

# 표준 주사위 면 번호 (마주보는 면 합 = 7)
FACE_LABELS = {
    (0, 0, 1): 1,   # +z 위
    (0, 0, -1): 6,  # -z 아래
    (1, 0, 0): 2,   # +x
    (-1, 0, 0): 5,  # -x
    (0, 1, 0): 3,   # +y
    (0, -1, 0): 4,  # -y
}

OUTPUT_DIR = "output"
