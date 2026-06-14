"""시뮬레이션 전역 설정 — 나중에 여기 숫자만 바꿔도 됩니다."""

# 주사위 크기: 한 변 1m, 중심이 원점 (0,0,0)
DIE_HALF_SIZE = 0.5  # 반쪽 길이 → 전체 [-0.5, 0.5]

# 밀도 격자 해상도 (12×12×12 = 1728칸 — 구 덩어리 형태 보존)
GRID_N = 12

# 낙하 조건
DROP_HEIGHT = 6.0       # 주사위 중심이 바닥 위 몇 m에서 시작할지
MAX_ANGULAR_VEL = 2.0   # 초기 각속도 최대값 (rad/s) — 낮을수록 관성·질량중심 효과↑

# 바닥 물성
FRICTION = 0.5
RESTITUTION = 0.75  # 반발계수 — 0=안 튕김, 1=완전 탄성

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
PNG_EXPORT_SUBDIR = "png"  # export PNG — output/png/ 에 일괄 저장
ARCHIVE_STUDIES_DIR = "archive_studies"  # ρ 스캔·구 밀도 실험 (대시보드 제외)

# 밀도 3D 색상 스케일 — 모든 시뮬레이션 동일 (ρ=0 파랑, ρ=1 흰색, ρ=6 빨강, 0~6 선형)
RHO_COLOR_MIN = 0.0
RHO_COLOR_MAX = 6.0
RHO_COLOR_BASELINE = 1.0

# ── 차트 제목 (config.py 숫자 조정 — 전체 refresh 없이 quick_refresh_charts.py 가능) ──
CHART_TITLE_MAIN_SIZE = 30       # 1줄 글자 크기(px)
CHART_TITLE_SUB_SIZE = 24        # 2줄 글자 크기(px)
CHART_TITLE_LINE_GAP = 6         # 1·2줄 사이 간격(px)
CHART_TITLE_TOP_PAD = 6          # 제목 위쪽 여백(px)
CHART_TITLE_MARGIN_TOP = 92      # 그래프 상단 margin (t)
CHART_TITLE_LINE_GAP_MOBILE = 0  # 모바일 HTML: 제목 2줄 간격
CHART_TITLE_MAIN_SIZE_MOBILE = round(CHART_TITLE_MAIN_SIZE * 0.9)
CHART_TITLE_SUB_SIZE_MOBILE = round(CHART_TITLE_SUB_SIZE * 0.9)
CHART_BAR_LABEL_SIZE_MOBILE = 10 # 모바일 HTML: 막대 위 확률 %
CHART_PROB_REF_LINE_WIDTH_MOBILE = 1.0  # 모바일 HTML: 균일 확률 점선 굵기 (데스크톱 1.5)

# ── 확률분포 HTML(대시보드) 레이아웃 — PNG(PROB_EXPORT_*)와 분리 ──
PROB_HTML_MARGIN = dict(t=CHART_TITLE_MARGIN_TOP, b=72, l=90, r=130)
PROB_HTML_LEGEND = dict(x=1.0, y=0.98, xanchor="left", yanchor="top")

# ── 질량분포 HTML(대시보드) 3D 영역 ──
DENSITY_AXIS_PAD_FACTOR = 0.42   # 클수록 정육면체가 작게·여유 있게 보임
DENSITY_CAMERA_EYE = dict(x=1.18, y=1.18, z=0.98)
DENSITY_CAMERA_CENTER = dict(x=0, y=0, z=0)
DENSITY_SCENE_X = (0.15, 0.70)   # 3D 영역 가운데
DENSITY_SCENE_Y = (0.16, 1.0)   # 제목에 가깝게 위로
DENSITY_HTML_COLORBAR_X = 1.0
DENSITY_HTML_COLORBAR_XANCHOR = "right"
DENSITY_HTML_MARGIN_R = 30
DENSITY_HTML_MARGIN_R_MOBILE = 0  # 모바일: ρ 범례 오른쪽 여백 없음
DENSITY_AXIS_PAD_FACTOR_MOBILE = 0.62  # 모바일: 클수록 정육면체 작게
DENSITY_AXIS_LIM_MOBILE = DIE_HALF_SIZE * (1 + DENSITY_AXIS_PAD_FACTOR_MOBILE)
DENSITY_CAMERA_EYE_MOBILE = dict(x=1.35, y=1.35, z=1.05)
DENSITY_HTML_COLORBAR_LEN = 0.58
DENSITY_HTML_COLORBAR_THICKNESS = 12
DENSITY_HTML_COLORBAR_X_MOBILE = 1.0
DENSITY_HTML_COLORBAR_XANCHOR_MOBILE = "right"
DENSITY_HTML_COLORBAR_THICKNESS_MOBILE = 10
DENSITY_HTML_COLORBAR_LEN_MOBILE = 0.50
DENSITY_HTML_SCENE_X_MOBILE = (0.0, 0.91)   # colorbar(오른쪽) 직전까지 3D 확장
DENSITY_HTML_SCENE_Y_MOBILE = (0.14, 0.92)
DENSITY_HTML_LEGEND = dict(x=0.005, y=0.01, xanchor="left", yanchor="bottom")

# ── 질량분포 PNG export 레이아웃 (보고서용 compact — HTML과 분리) ──
DENSITY_EXPORT_AXIS_PAD_FACTOR = 0.30   # 축 끝 여유 (작을수록 좌우 빈 공간↓)
DENSITY_EXPORT_SCENE_X = (0.0, 0.995)
DENSITY_EXPORT_SCENE_Y = (0.08, 0.99)
DENSITY_EXPORT_CAMERA_EYE = dict(x=1.12, y=1.12, z=0.98)
DENSITY_EXPORT_CAMERA_CENTER = dict(x=0, y=0, z=0)
DENSITY_EXPORT_MARGIN = dict(l=0, r=0, b=0, t=0)
DENSITY_EXPORT_TITLE_MARGIN_TOP = 54
DENSITY_EXPORT_COLORBAR_GAP = -0.04   # 음수=왼쪽, 0=주사위 닿기 직전
DENSITY_EXPORT_COLORBAR_LEN = 0.82
DENSITY_EXPORT_COLORBAR_THICKNESS = 7
DENSITY_EXPORT_LEGEND = dict(x=0.12, y=0.11, xanchor="left", yanchor="bottom")
DENSITY_EXPORT_PNG_KW = dict(width=1000, height=720, scale=2)

# ── 확률분포 PNG export 레이아웃 (보고서용 compact — HTML과 분리) ──
PROB_EXPORT_PNG_KW = dict(width=1000, height=720, scale=2)
PROB_EXPORT_TITLE_MARGIN_TOP = 54
PROB_EXPORT_MARGIN = dict(t=54, b=58, l=58, r=52)
PROB_EXPORT_AXIS_TITLE_SIZE = 13
PROB_EXPORT_AXIS_TICK_SIZE = 12
PROB_EXPORT_BAR_LABEL_SIZE = 14
PROB_EXPORT_FONT_SIZE = 12
PROB_EXPORT_LEGEND_SIZE = 11
