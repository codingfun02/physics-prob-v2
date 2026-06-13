"""보고서·대시보드용 접근성 색상 (SSP 스타일 2색 조합 기반)."""

from __future__ import annotations

# Gray Blue
GRAY_BLUE_LIGHT = "#97a6c4"
GRAY_BLUE_DARK = "#384860"

# Sequential Blue
BLUE_LIGHT = "#8cc5e3"
BLUE_MED = "#1a80bb"

# Contrasting pairs
RED_DARK = "#a00000"
TEAL_MED = "#298c8c"
GOLD = "#f1a226"
ORANGE = "#ea801c"
GRAY_DARK = "#707070"
GRAY_LIGHT = "#b8b8b8"

# Chrome
TEXT = GRAY_BLUE_DARK
GRID = "#e8e8e8"
AXIS = GRAY_LIGHT
REF_LINE = GRAY_DARK
PROB_REF_LINE = "#ffa600"
PROB_ERROR_COLOR = GRAY_BLUE_DARK

# 확률 막대: 밝은 파랑·빨강 교차
RED_BRIGHT = "#e85d5d"
PROB_BAR_FACE_COLORS = [
    BLUE_LIGHT,
    RED_BRIGHT,
    BLUE_LIGHT,
    RED_BRIGHT,
    BLUE_LIGHT,
    RED_BRIGHT,
]

# 단일 막대그래프 (레거시 alias)
BAR_FACE_COLORS = PROB_BAR_FACE_COLORS

# 다중 시리즈 비교
COMPARISON_COLORS = [
    BLUE_MED,
    RED_DARK,
    TEAL_MED,
    GOLD,
    ORANGE,
    GRAY_BLUE_DARK,
    "#800074",
    GRAY_DARK,
    GRAY_BLUE_LIGHT,
    "#f2c45f",
]

# 밀도 3D: 저밀도(파랑) — 기준(흰색) — 고밀도(빨강)
RHO_DIVERGING_SCALE = [
    [0.0, BLUE_MED],
    [0.5, "#ffffff"],
    [1.0, RED_DARK],
]

# 확률 히트맵
PROB_HEATMAP_SCALE = RHO_DIVERGING_SCALE
