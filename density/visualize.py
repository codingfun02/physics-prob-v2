"""Plotly로 밀도 격자를 3D 색상으로 시각화."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from config import (
    CHART_TITLE_MARGIN_TOP,
    DIE_HALF_SIZE,
    DENSITY_AXIS_PAD_FACTOR,
    DENSITY_CAMERA_CENTER,
    DENSITY_CAMERA_EYE,
    DENSITY_EXPORT_AXIS_PAD_FACTOR,
    DENSITY_EXPORT_CAMERA_CENTER,
    DENSITY_EXPORT_CAMERA_EYE,
    DENSITY_EXPORT_COLORBAR_GAP,
    DENSITY_EXPORT_COLORBAR_LEN,
    DENSITY_EXPORT_COLORBAR_THICKNESS,
    DENSITY_EXPORT_LEGEND,
    DENSITY_EXPORT_MARGIN,
    DENSITY_EXPORT_PNG_KW,
    DENSITY_EXPORT_SCENE_X,
    DENSITY_EXPORT_SCENE_Y,
    DENSITY_EXPORT_TITLE_MARGIN_TOP,
    DENSITY_HTML_COLORBAR_LEN,
    DENSITY_HTML_COLORBAR_THICKNESS,
    DENSITY_HTML_COLORBAR_X,
    DENSITY_HTML_COLORBAR_XANCHOR,
    DENSITY_HTML_LEGEND,
    DENSITY_HTML_MARGIN_R,
    DENSITY_SCENE_X,
    DENSITY_SCENE_Y,
    FACE_LABELS,
    OUTPUT_DIR,
    RHO_COLOR_BASELINE,
    RHO_COLOR_MAX,
    RHO_COLOR_MIN,
)
from physics.inertia import InertiaProperties, compute_inertia
from simulation.chart_palette import (
    BLUE_MED,
    GOLD,
    GRAY_DARK,
    RED_DARK,
    TEAL_MED,
    TEXT,
)
from simulation.chart_title import apply_two_line_title
from simulation.plotly_export import try_write_png_export, write_plotly_html
from .grid import RhoGrid

# 정육면체 8꼭짓점 + 12삼각형 (6면)
_CUBE_I = [7, 0, 0, 0, 4, 4, 6, 1, 4, 0, 3, 6]
_CUBE_J = [3, 4, 1, 2, 5, 6, 5, 2, 7, 1, 6, 3]
_CUBE_K = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 2]

_BASELINE_RHO = RHO_COLOR_BASELINE
_BUMP_RHO_EPS = 1e-4


# ρ−1 → 파랑, 기준(ρ=1) → 흰색, 고밀도 → 빨강 — ρ 0~6 선형 눈금
def _rho_baseline_t() -> float:
    span = RHO_COLOR_MAX - RHO_COLOR_MIN
    if span <= 0:
        return 0.5
    return float((_BASELINE_RHO - RHO_COLOR_MIN) / span)


RHO_COLORSCALE = [
    [0.0, BLUE_MED],
    [_rho_baseline_t(), "#ffffff"],
    [1.0, RED_DARK],
]


def _rho_to_color_t(rho_val: float) -> float:
    """
    밀도 → 색상 강도 [0, 1] (ρ 0~6 선형, colorbar 눈금과 일치).

    ρ=0 → 0, ρ=1 → 1/6(흰색), ρ=6 → 1.
    """
    rho = float(rho_val)
    span = RHO_COLOR_MAX - RHO_COLOR_MIN
    if span <= 0:
        return 0.5
    return float((rho - RHO_COLOR_MIN) / span)


def _density_export_colorbar_x() -> float:
    """PNG: ρ colorbar를 3D 콘텐츠(주사위) 오른쪽 끝 + gap에 맞춤."""
    x0, x1 = DENSITY_EXPORT_SCENE_X
    scene_w = x1 - x0
    cx = x0 + scene_w * 0.5
    half = scene_w * 0.5 / (1.0 + DENSITY_EXPORT_AXIS_PAD_FACTOR)
    cube_right = cx + half
    return cube_right + DENSITY_EXPORT_COLORBAR_GAP


def _rho_colorbar(*, for_export: bool = False) -> dict:
    """ρ 범례 — intensity↔실제 ρ 고정 매핑."""
    tick_rhos = [0, 1, 2, 3, 4, 5, 6]
    tickvals = [_rho_to_color_t(r) for r in tick_rhos]
    ticktext = [f"{r:g}" for r in tick_rhos]
    if for_export:
        x = _density_export_colorbar_x()
        xanchor = "left"
        length = DENSITY_EXPORT_COLORBAR_LEN
        thickness = DENSITY_EXPORT_COLORBAR_THICKNESS
    else:
        x = DENSITY_HTML_COLORBAR_X
        xanchor = DENSITY_HTML_COLORBAR_XANCHOR
        length = DENSITY_HTML_COLORBAR_LEN
        thickness = DENSITY_HTML_COLORBAR_THICKNESS
    return dict(
        title="ρ",
        tickvals=tickvals,
        ticktext=ticktext,
        x=x,
        xanchor=xanchor,
        y=0.5,
        yanchor="middle",
        len=length,
        thickness=thickness,
    )


def _append_cell(
    xs: list[float],
    ys: list[float],
    zs: list[float],
    ii: list[int],
    jj: list[int],
    kk: list[int],
    intensity: list[float],
    vertex_offset: int,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
    color_t: float,
) -> int:
    corners_x = [x0, x1, x1, x0, x0, x1, x1, x0]
    corners_y = [y0, y0, y1, y1, y0, y0, y1, y1]
    corners_z = [z0, z0, z0, z0, z1, z1, z1, z1]

    xs.extend(corners_x)
    ys.extend(corners_y)
    zs.extend(corners_z)
    intensity.extend([color_t] * 8)

    for a, b, c in zip(_CUBE_I, _CUBE_J, _CUBE_K):
        ii.append(vertex_offset + a)
        jj.append(vertex_offset + b)
        kk.append(vertex_offset + c)

    return vertex_offset + 8


def _is_baseline(val: float) -> bool:
    return abs(val - _BASELINE_RHO) <= _BUMP_RHO_EPS


def _face_exposed(rho: np.ndarray, i: int, j: int, k: int, n: int, val: float, di: int, dj: int, dk: int) -> bool:
    """이웃과 밀도가 다르거나 격자 바깥이면 면을 노출."""
    ni, nj, nk = i + di, j + dj, k + dk
    if 0 <= ni < n and 0 <= nj < n and 0 <= nk < n:
        return abs(float(rho[ni, nj, nk]) - val) > _BUMP_RHO_EPS
    return True


def _greedy_rectangles(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """2D 마스크에서 인접 사각형 병합 (j0, j1, k0, k1) half-open."""
    n_j, n_k = mask.shape
    used = np.zeros_like(mask, dtype=bool)
    rects: list[tuple[int, int, int, int]] = []
    for j in range(n_j):
        for k in range(n_k):
            if not mask[j, k] or used[j, k]:
                continue
            k1 = k + 1
            while k1 < n_k and mask[j, k1] and not used[j, k1]:
                k1 += 1
            j1 = j + 1
            while j1 < n_j and np.all(mask[j1, k:k1]) and not np.any(used[j1, k:k1]):
                j1 += 1
            rects.append((j, j1, k, k1))
            used[j:j1, k:k1] = True
    return rects


def _append_quad(
    xs: list[float],
    ys: list[float],
    zs: list[float],
    ii: list[int],
    jj: list[int],
    kk: list[int],
    intensity: list[float],
    corners: tuple[tuple[float, float, float], ...],
    color_t: float,
) -> None:
    """사각 면 → 삼각형 2개."""
    off = len(xs)
    for x, y, z in corners:
        xs.append(x)
        ys.append(y)
        zs.append(z)
        intensity.append(color_t)
    ii.extend([off, off])
    jj.extend([off + 1, off + 2])
    kk.extend([off + 2, off + 3])


def _emit_merged_faces(
    mesh: dict,
    mask: np.ndarray,
    colors: np.ndarray,
    emit_rect,
) -> None:
    """같은 색상끼리 greedy 병합 후 사각 면 추가."""
    if not mask.any():
        return
    active_colors = np.unique(colors[mask])
    for color_t in active_colors:
        sub = mask & np.isclose(colors, color_t)
        for j0, j1, k0, k1 in _greedy_rectangles(sub):
            emit_rect(mesh, j0, j1, k0, k1, float(color_t))


def _extract_dev_surface_mesh(rho: np.ndarray, axis_ticks: np.ndarray, n: int) -> dict:
    """ρ≠1 영역의 표면만 추출·병합 (내부 ρ=1 부피는 그리지 않음)."""
    mesh: dict = {k: [] for k in ("xs", "ys", "zs", "ii", "jj", "kk", "intensity")}

    def neg_x_rect(m, j0, j1, k0, k1, color_t, *, i: int):
        x = float(axis_ticks[i])
        y0, y1 = float(axis_ticks[j0]), float(axis_ticks[j1])
        z0, z1 = float(axis_ticks[k0]), float(axis_ticks[k1])
        _append_quad(
            m["xs"], m["ys"], m["zs"], m["ii"], m["jj"], m["kk"], m["intensity"],
            ((x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)),
            color_t,
        )

    def pos_x_rect(m, j0, j1, k0, k1, color_t, *, i: int):
        x = float(axis_ticks[i + 1])
        y0, y1 = float(axis_ticks[j0]), float(axis_ticks[j1])
        z0, z1 = float(axis_ticks[k0]), float(axis_ticks[k1])
        _append_quad(
            m["xs"], m["ys"], m["zs"], m["ii"], m["jj"], m["kk"], m["intensity"],
            ((x, y0, z1), (x, y1, z1), (x, y1, z0), (x, y0, z0)),
            color_t,
        )

    def neg_y_rect(m, j0, j1, k0, k1, color_t, *, i: int):
        y = float(axis_ticks[i])
        x0, x1 = float(axis_ticks[j0]), float(axis_ticks[j1])
        z0, z1 = float(axis_ticks[k0]), float(axis_ticks[k1])
        _append_quad(
            m["xs"], m["ys"], m["zs"], m["ii"], m["jj"], m["kk"], m["intensity"],
            ((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)),
            color_t,
        )

    def pos_y_rect(m, j0, j1, k0, k1, color_t, *, i: int):
        y = float(axis_ticks[i + 1])
        x0, x1 = float(axis_ticks[j0]), float(axis_ticks[j1])
        z0, z1 = float(axis_ticks[k0]), float(axis_ticks[k1])
        _append_quad(
            m["xs"], m["ys"], m["zs"], m["ii"], m["jj"], m["kk"], m["intensity"],
            ((x0, y, z1), (x1, y, z1), (x1, y, z0), (x0, y, z0)),
            color_t,
        )

    def neg_z_rect(m, j0, j1, k0, k1, color_t, *, i: int):
        z = float(axis_ticks[i])
        x0, x1 = float(axis_ticks[j0]), float(axis_ticks[j1])
        y0, y1 = float(axis_ticks[k0]), float(axis_ticks[k1])
        _append_quad(
            m["xs"], m["ys"], m["zs"], m["ii"], m["jj"], m["kk"], m["intensity"],
            ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)),
            color_t,
        )

    def pos_z_rect(m, j0, j1, k0, k1, color_t, *, i: int):
        z = float(axis_ticks[i + 1])
        x0, x1 = float(axis_ticks[j0]), float(axis_ticks[j1])
        y0, y1 = float(axis_ticks[k0]), float(axis_ticks[k1])
        _append_quad(
            m["xs"], m["ys"], m["zs"], m["ii"], m["jj"], m["kk"], m["intensity"],
            ((x0, y1, z), (x1, y1, z), (x1, y0, z), (x0, y0, z)),
            color_t,
        )

    for i in range(n):
        mask = np.zeros((n, n), dtype=bool)
        colors = np.zeros((n, n))
        for j in range(n):
            for k in range(n):
                val = float(rho[i, j, k])
                if _is_baseline(val):
                    continue
                if _face_exposed(rho, i, j, k, n, val, -1, 0, 0):
                    mask[j, k] = True
                    colors[j, k] = _rho_to_color_t(val)
        _emit_merged_faces(mesh, mask, colors, lambda m, *a, **kw: neg_x_rect(m, *a, **kw, i=i))

        mask[:] = False
        colors[:] = 0
        for j in range(n):
            for k in range(n):
                val = float(rho[i, j, k])
                if _is_baseline(val):
                    continue
                if _face_exposed(rho, i, j, k, n, val, 1, 0, 0):
                    mask[j, k] = True
                    colors[j, k] = _rho_to_color_t(val)
        _emit_merged_faces(mesh, mask, colors, lambda m, *a, **kw: pos_x_rect(m, *a, **kw, i=i))

    for j in range(n):
        mask = np.zeros((n, n), dtype=bool)
        colors = np.zeros((n, n))
        for i in range(n):
            for k in range(n):
                val = float(rho[i, j, k])
                if _is_baseline(val):
                    continue
                if _face_exposed(rho, i, j, k, n, val, 0, -1, 0):
                    mask[i, k] = True
                    colors[i, k] = _rho_to_color_t(val)
        _emit_merged_faces(mesh, mask, colors, lambda m, *a, **kw: neg_y_rect(m, *a, **kw, i=j))

        mask[:] = False
        colors[:] = 0
        for i in range(n):
            for k in range(n):
                val = float(rho[i, j, k])
                if _is_baseline(val):
                    continue
                if _face_exposed(rho, i, j, k, n, val, 0, 1, 0):
                    mask[i, k] = True
                    colors[i, k] = _rho_to_color_t(val)
        _emit_merged_faces(mesh, mask, colors, lambda m, *a, **kw: pos_y_rect(m, *a, **kw, i=j))

    for k in range(n):
        mask = np.zeros((n, n), dtype=bool)
        colors = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                val = float(rho[i, j, k])
                if _is_baseline(val):
                    continue
                if _face_exposed(rho, i, j, k, n, val, 0, 0, -1):
                    mask[i, j] = True
                    colors[i, j] = _rho_to_color_t(val)
        _emit_merged_faces(mesh, mask, colors, lambda m, *a, **kw: neg_z_rect(m, *a, **kw, i=k))

        mask[:] = False
        colors[:] = 0
        for i in range(n):
            for j in range(n):
                val = float(rho[i, j, k])
                if _is_baseline(val):
                    continue
                if _face_exposed(rho, i, j, k, n, val, 0, 0, 1):
                    mask[i, j] = True
                    colors[i, j] = _rho_to_color_t(val)
        _emit_merged_faces(mesh, mask, colors, lambda m, *a, **kw: pos_z_rect(m, *a, **kw, i=k))

    return mesh


def _uniform_box_mesh(half: float, color_t: float) -> dict:
    """균일 ρ=1 — 정육면체 하나."""
    mesh: dict = {k: [] for k in ("xs", "ys", "zs", "ii", "jj", "kk", "intensity")}
    _append_cell(
        mesh["xs"], mesh["ys"], mesh["zs"],
        mesh["ii"], mesh["jj"], mesh["kk"], mesh["intensity"],
        0, -half, half, -half, half, -half, half, color_t,
    )
    return mesh


def _scene_axis(half: float, title: str) -> dict:
    pad = half * DENSITY_AXIS_PAD_FACTOR
    lim = half + pad
    return dict(
        title=title,
        range=[-lim, lim],
        autorange=False,
        backgroundcolor="rgb(252,252,253)",
    )


def _scene_camera(half: float) -> dict:
    """주사위가 화면 중앙에 작게·안정적으로 보이도록 카메라."""
    return dict(
        eye=DENSITY_CAMERA_EYE,
        center=DENSITY_CAMERA_CENTER,
        up=dict(x=0, y=0, z=1),
    )


def _make_mesh_trace(
    xs: list[float],
    ys: list[float],
    zs: list[float],
    ii: list[int],
    jj: list[int],
    kk: list[int],
    intensity: list[float],
    *,
    opacity: float,
    name: str,
    colorbar: dict | None,
    showscale: bool,
) -> go.Mesh3d:
    return go.Mesh3d(
        x=xs,
        y=ys,
        z=zs,
        i=ii,
        j=jj,
        k=kk,
        intensity=intensity,
        colorscale=RHO_COLORSCALE,
        cmin=0,
        cmax=1,
        opacity=opacity,
        flatshading=True,
        lighting=dict(ambient=0.92, diffuse=0.45, specular=0.15, roughness=0.85),
        colorbar=colorbar,
        showscale=showscale,
        hoverinfo="skip",
        name=name,
        showlegend=False,
    )


def _die_face_labels(half: float) -> go.Scatter3d:
    """주사위 6면 바깥에 눈(1~6) 표시."""
    pad = half * 0.06
    axis_hint = {
        (1, 0, 0): "+x",
        (-1, 0, 0): "−x",
        (0, 1, 0): "+y",
        (0, -1, 0): "−y",
        (0, 0, 1): "+z (위)",
        (0, 0, -1): "−z (아래)",
    }
    xs, ys, zs, texts, hovers = [], [], [], [], []
    for normal, face_num in FACE_LABELS.items():
        nx, ny, nz = normal
        r = half + pad
        xs.append(nx * r)
        ys.append(ny * r)
        zs.append(nz * r)
        texts.append(str(face_num))
        hint = axis_hint.get(normal, "")
        hovers.append(f"눈 {face_num}" + (f" ({hint})" if hint else ""))

    return go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="text",
        text=texts,
        textfont=dict(size=22, color=TEXT, family="Arial, Helvetica, sans-serif"),
        textposition="middle center",
        hovertext=hovers,
        hoverinfo="text",
        name="눈 (1~6)",
        showlegend=False,
    )


def _die_wireframe(half: float) -> go.Scatter3d:
    """주사위 외곽 — 내부 구조 파악용."""
    c = [
        [-1, -1, -1],
        [1, -1, -1],
        [1, 1, -1],
        [-1, 1, -1],
        [-1, -1, 1],
        [1, -1, 1],
        [1, 1, 1],
        [-1, 1, 1],
    ]
    pts = np.array(c, dtype=float) * half
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    xs, ys, zs = [], [], []
    for a, b in edges:
        xs.extend([pts[a, 0], pts[b, 0], None])
        ys.extend([pts[a, 1], pts[b, 1], None])
        zs.extend([pts[a, 2], pts[b, 2], None])
    return go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="lines",
        line=dict(color=GRAY_DARK, width=2),
        hoverinfo="skip",
        name="외곽",
        showlegend=False,
    )


def _physics_annotation_text(props: InertiaProperties, grid_n: int) -> str:
    """차트 좌상단 물리량 요약 (Plotly annotation HTML)."""
    com = props.com
    ixx, iyy, izz = np.diag(props.inertia_tensor)
    i1, i2, i3 = props.principal_moments
    i_mean = float(np.mean(props.principal_moments))
    asym = (float(i3 - i1) / i_mean * 100) if i_mean > 0 else 0.0
    off_diag = props.inertia_tensor.copy()
    np.fill_diagonal(off_diag, 0.0)
    max_off = float(np.max(np.abs(off_diag)))

    return "<br>".join(
        [
            f"<b>격자 물리량</b> ({grid_n}³)",
            f"M = {props.mass:.4f}",
            f"질량중심 (x,y,z) = ({com[0]:.4f}, {com[1]:.4f}, {com[2]:.4f})",
            f"기하중심 편차 = ({com[0]:.4f}, {com[1]:.4f}, {com[2]:.4f})",
            f"Ixx, Iyy, Izz = {ixx:.5f}, {iyy:.5f}, {izz:.5f}",
            f"주관성 I₁, I₂, I₃ = {i1:.5f}, {i2:.5f}, {i3:.5f}",
            f"관성 비대칭 = {asym:.2f}%",
            f"비대각 |I|max = {max_off:.2e}",
        ]
    )


def _com_offset_trace(com: np.ndarray) -> list[go.Scatter3d]:
    """원점(0,0,0)과 질량중심 마커·연결선."""
    traces: list[go.Scatter3d] = []
    traces.append(
        go.Scatter3d(
            x=[0.0],
            y=[0.0],
            z=[0.0],
            mode="markers",
            marker=dict(
                size=14,
                color=TEAL_MED,
                symbol="circle",
                line=dict(color="rgb(255, 255, 255)", width=2),
            ),
            name="원점",
            hovertemplate="원점 (0, 0, 0)<extra></extra>",
        )
    )
    traces.append(
        go.Scatter3d(
            x=[float(com[0])],
            y=[float(com[1])],
            z=[float(com[2])],
            mode="markers",
            marker=dict(
                size=16,
                color=GOLD,
                symbol="diamond",
                line=dict(color="rgb(255, 255, 255)", width=2),
            ),
            name="질량중심",
            hovertemplate=(
                "질량중심<br>"
                f"x={com[0]:.4f}, y={com[1]:.4f}, z={com[2]:.4f}<extra></extra>"
            ),
        )
    )
    offset = float(np.linalg.norm(com))
    if offset > 1e-5:
        traces.append(
            go.Scatter3d(
                x=[0.0, float(com[0])],
                y=[0.0, float(com[1])],
                z=[0.0, float(com[2])],
                mode="lines",
                line=dict(color=GOLD, width=5),
                name="원점→질량중심",
                hoverinfo="skip",
                showlegend=False,
            )
        )
    return traces


def _principal_axis_traces(props: InertiaProperties, half: float) -> list[go.Scatter3d]:
    """질량중심에서 주관성 축 방향 선."""
    axes = props.principal_rotation.as_matrix()
    com = props.com
    i_max = float(props.principal_moments.max())
    if i_max <= 0:
        return []

    colors = ["#2563eb", "#16a34a", "#dc2626"]
    labels = ["주축 1 (I₁)", "주축 2 (I₂)", "주축 3 (I₃)"]
    traces: list[go.Scatter3d] = []
    for i in range(3):
        direction = axes[:, i]
        length = half * 0.35 * float(np.sqrt(props.principal_moments[i] / i_max))
        end = com + direction * length
        traces.append(
            go.Scatter3d(
                x=[float(com[0]), float(end[0])],
                y=[float(com[1]), float(end[1])],
                z=[float(com[2]), float(end[2])],
                mode="lines",
                line=dict(color=colors[i], width=5),
                name=labels[i],
                hovertemplate=(
                    f"{labels[i]} = {props.principal_moments[i]:.5f}<extra></extra>"
                ),
            )
        )
    return traces


def _export_scene_axis(half: float, title: str) -> dict:
    pad = half * DENSITY_EXPORT_AXIS_PAD_FACTOR
    lim = half + pad
    return dict(
        title=dict(text=title, font=dict(size=12, color="rgb(80, 80, 80)")),
        tickfont=dict(size=10, color="rgb(100, 100, 100)"),
        range=[-lim, lim],
        autorange=False,
        showticklabels=True,
        backgroundcolor="rgb(252,252,253)",
    )


def _sync_rho_colorscale(
    fig: go.Figure,
    *,
    colorbar_overrides: dict | None = None,
) -> None:
    """ρ→색 비율·colorbar 눈금을 모든 질량분포 차트에서 동일하게."""
    bar = _rho_colorbar(for_export=bool(colorbar_overrides))
    if colorbar_overrides:
        bar = {**bar, **colorbar_overrides}
    for trace in fig.data:
        if getattr(trace, "type", None) != "mesh3d":
            continue
        trace.update(colorscale=RHO_COLORSCALE, cmin=0, cmax=1)
        if getattr(trace, "showscale", False) and getattr(trace, "colorbar", None):
            trace.colorbar.update(bar)


def _prep_density_png_export(fig: go.Figure) -> None:
    """PNG 저장 시 3D 영역·카메라·여백 (config.py DENSITY_EXPORT_*)."""
    half = DIE_HALF_SIZE
    if fig.layout.scene and fig.layout.scene.xaxis and fig.layout.scene.xaxis.range:
        half = float(fig.layout.scene.xaxis.range[1]) / (
            1 + DENSITY_EXPORT_AXIS_PAD_FACTOR
        )
    fig.update_layout(
        autosize=False,
        scene=dict(
            xaxis=_export_scene_axis(half, "x"),
            yaxis=_export_scene_axis(half, "y"),
            zaxis=_export_scene_axis(half, "z"),
            domain=dict(x=list(DENSITY_EXPORT_SCENE_X), y=list(DENSITY_EXPORT_SCENE_Y)),
            camera=dict(eye=DENSITY_EXPORT_CAMERA_EYE, center=DENSITY_EXPORT_CAMERA_CENTER),
        ),
        margin={**DENSITY_EXPORT_MARGIN, "t": DENSITY_EXPORT_TITLE_MARGIN_TOP},
        legend=dict(
            bgcolor="rgba(255, 255, 255, 0.92)",
            bordercolor="rgb(203, 213, 225)",
            borderwidth=1,
            font=dict(size=10),
            **DENSITY_EXPORT_LEGEND,
        ),
    )
    _sync_rho_colorscale(
        fig,
        colorbar_overrides=dict(
            x=_density_export_colorbar_x(),
            len=DENSITY_EXPORT_COLORBAR_LEN,
            thickness=DENSITY_EXPORT_COLORBAR_THICKNESS,
        ),
    )


def plot_rho_grid(
    grid: RhoGrid,
    title: str | tuple[str, str | None] = "주사위 밀도 분포 ρ(x,y,z)",
    save_path: str | Path | None = None,
    show: bool = True,
    face_opacity: float = 0.35,
    base_opacity: float | None = None,
    bump_opacity: float | None = None,
    show_physics: bool = True,
) -> go.Figure:
    """
    밀도 격자를 3D로 시각화합니다.

    - ρ≠1: 표면만 추출·병합 (같은 밀도 = 하나의 덩어리)
    - ρ=1 내부 부피: bump 있을 때 생략 (가림 방지)
    - 정육면체 wireframe으로 전체 윤곽 표시
    - 6면 바깥에 눈(1~6) 번호 표시
    - 균일 ρ=1: 정육면체 하나만 표시
    """
    if isinstance(title, tuple):
        line1, line2 = title
    else:
        line1, line2 = str(title), None

    n = grid.n
    half = grid.half_size
    rho = grid.rho
    rho_min, rho_max = float(rho.min()), float(rho.max())
    has_bump = (
        rho_max > _BASELINE_RHO + _BUMP_RHO_EPS
        or rho_min < _BASELINE_RHO - _BUMP_RHO_EPS
    )

    if bump_opacity is None:
        bump_opacity = 0.92 if has_bump else face_opacity
    if base_opacity is None:
        base_opacity = face_opacity

    axis_ticks = np.linspace(-half, half, n + 1)
    colorbar = _rho_colorbar()
    fig = go.Figure()

    fig.add_trace(_die_wireframe(half))

    if has_bump:
        dev_mesh = _extract_dev_surface_mesh(rho, axis_ticks, n)
        if dev_mesh["xs"]:
            fig.add_trace(
                _make_mesh_trace(
                    dev_mesh["xs"], dev_mesh["ys"], dev_mesh["zs"],
                    dev_mesh["ii"], dev_mesh["jj"], dev_mesh["kk"],
                    dev_mesh["intensity"],
                    opacity=bump_opacity,
                    name="ρ≠1",
                    colorbar=colorbar,
                    showscale=True,
                )
            )
    else:
        uniform = _uniform_box_mesh(half, _rho_to_color_t(_BASELINE_RHO))
        fig.add_trace(
            _make_mesh_trace(
                uniform["xs"], uniform["ys"], uniform["zs"],
                uniform["ii"], uniform["jj"], uniform["kk"],
                uniform["intensity"],
                opacity=base_opacity,
                name="ρ=1 (균일)",
                colorbar=colorbar,
                showscale=True,
            )
        )

    fig.add_trace(_die_face_labels(half))

    if show_physics:
        props = compute_inertia(grid)
        for trace in _com_offset_trace(props.com):
            fig.add_trace(trace)

    fig.update_layout(
        scene=dict(
            xaxis=_scene_axis(half, "x"),
            yaxis=_scene_axis(half, "y"),
            zaxis=_scene_axis(half, "z"),
            aspectmode="cube",
            camera=_scene_camera(half),
            domain=dict(x=list(DENSITY_SCENE_X), y=list(DENSITY_SCENE_Y)),
        ),
        margin=dict(l=6, r=DENSITY_HTML_MARGIN_R, t=CHART_TITLE_MARGIN_TOP, b=8),
        legend=dict(
            bgcolor="rgba(255, 255, 255, 0.92)",
            bordercolor="rgb(203, 213, 225)",
            borderwidth=1,
            font=dict(size=11),
            **DENSITY_HTML_LEGEND,
        ),
        showlegend=True,
    )
    apply_two_line_title(fig, line1, line2)
    _sync_rho_colorscale(fig)

    if save_path is None:
        save_path = Path(OUTPUT_DIR) / "rho_density.html"
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    write_plotly_html(fig, save_path, chart_kind="density")
    try_write_png_export(
        fig,
        save_path,
        prep=_prep_density_png_export,
        png_kw=DENSITY_EXPORT_PNG_KW,
    )

    if show:
        fig.show()

    return fig
