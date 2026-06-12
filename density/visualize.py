"""Plotly로 6×6×6 밀도 격자를 3D 색상으로 시각화."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from config import OUTPUT_DIR
from .grid import RhoGrid

# 정육면체 8꼭짓점 + 12삼각형 (6면)
_CUBE_I = [7, 0, 0, 0, 4, 4, 6, 1, 4, 0, 3, 6]
_CUBE_J = [3, 4, 1, 2, 5, 6, 5, 2, 7, 1, 6, 3]
_CUBE_K = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 2]
# 밀도 낮음(빨강) → 높음(파랑)
RHO_COLORSCALE = [
    [0.0, "rgb(220, 60, 60)"],
    [0.5, "rgb(240, 240, 240)"],
    [1.0, "rgb(60, 80, 220)"],
]


def plot_rho_grid(
    grid: RhoGrid,
    title: str = "주사위 밀도 분포 ρ(x,y,z)",
    save_path: str | Path | None = None,
    show: bool = True,
    face_opacity: float = 0.35,
) -> go.Figure:
    """
    216개 소셀을 반투명 정육면체로 그립니다.

    - 각 셀: 6면이 있는 작은 상자 (면 투명도로 내부가 보임)
    - 색: 빨강(낮은 ρ) → 파랑(높은 ρ)
    """
    n = grid.n
    half = grid.half_size
    rho = grid.rho
    rho_min, rho_max = float(rho.min()), float(rho.max())

    axis_ticks = np.linspace(-half, half, n + 1)

    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    ii: list[int] = []
    jj: list[int] = []
    kk: list[int] = []
    intensity: list[float] = []
    vertex_offset = 0

    for i in range(n):
        for j in range(n):
            for k in range(n):
                x0, x1 = axis_ticks[i], axis_ticks[i + 1]
                y0, y1 = axis_ticks[j], axis_ticks[j + 1]
                z0, z1 = axis_ticks[k], axis_ticks[k + 1]
                val = float(rho[i, j, k])

                # 정규화 밀도 (색상용)
                if rho_max > rho_min:
                    t = (val - rho_min) / (rho_max - rho_min)
                else:
                    t = 0.5

                # 8꼭짓점 (셀마다 독립 — 면이 셀 경계에서 구분됨)
                corners_x = [x0, x1, x1, x0, x0, x1, x1, x0]
                corners_y = [y0, y0, y1, y1, y0, y0, y1, y1]
                corners_z = [z0, z0, z0, z0, z1, z1, z1, z1]

                xs.extend(corners_x)
                ys.extend(corners_y)
                zs.extend(corners_z)
                intensity.extend([t] * 8)

                for a, b, c in zip(_CUBE_I, _CUBE_J, _CUBE_K):
                    ii.append(vertex_offset + a)
                    jj.append(vertex_offset + b)
                    kk.append(vertex_offset + c)

                vertex_offset += 8

    # 셀 중심에 호버용 보이지 않는 점
    centers = grid.cell_centers.reshape(-1, 3)
    cell_vals = rho.reshape(-1)

    fig = go.Figure()

    fig.add_trace(
        go.Mesh3d(
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
            opacity=face_opacity,
            flatshading=True,
            lighting=dict(ambient=0.85, diffuse=0.5, specular=0.2, roughness=0.9),
            colorbar=dict(
                title="ρ (정규화)",
                tickvals=[0, 0.5, 1],
                ticktext=[
                    f"낮음 ({rho_min:.3g})",
                    f"{(rho_min + rho_max) / 2:.3g}",
                    f"높음 ({rho_max:.3g})",
                ],
            ),
            hoverinfo="skip",
            name="밀도 셀",
        )
    )

    fig.add_trace(
        go.Scatter3d(
            x=centers[:, 0],
            y=centers[:, 1],
            z=centers[:, 2],
            mode="markers",
            marker=dict(size=2, opacity=0),
            text=[f"ρ={v:.4f}" for v in cell_vals],
            hovertemplate="%{text}<extra></extra>",
            name="셀 정보",
        )
    )

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="x",
            yaxis_title="y",
            zaxis_title="z",
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(x=0.01, y=0.99),
    )

    if save_path is None:
        save_path = Path(OUTPUT_DIR) / "rho_density.html"
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(save_path))

    if show:
        fig.show()

    return fig
