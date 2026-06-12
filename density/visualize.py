"""Plotly로 6×6×6 밀도 격자를 3D 색상으로 시각화."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from config import OUTPUT_DIR
from .grid import RhoGrid


def plot_rho_grid(
    grid: RhoGrid,
    title: str = "주사위 밀도 분포 ρ(x,y,z)",
    save_path: str | Path | None = None,
    show: bool = True,
) -> go.Figure:
    """
    216개 소셀을 작은 정육면체로 그리고, 밀도가 높을수록 진한 색으로 표시합니다.

    색이 진할수록 = 그 칸이 더 무겁다는 뜻입니다.
    """
    n = grid.n
    cs = grid.cell_size
    half = grid.half_size
    rho = grid.rho
    rho_min, rho_max = float(rho.min()), float(rho.max())

    fig = go.Figure()
    axis_ticks = np.linspace(-half, half, n + 1)

    for i in range(n):
        for j in range(n):
            for k in range(n):
                x0, x1 = axis_ticks[i], axis_ticks[i + 1]
                y0, y1 = axis_ticks[j], axis_ticks[j + 1]
                z0, z1 = axis_ticks[k], axis_ticks[k + 1]
                val = rho[i, j, k]

                # 밀도 → 0~1 사이 값 (색 농도)
                if rho_max > rho_min:
                    intensity = (val - rho_min) / (rho_max - rho_min)
                else:
                    intensity = 0.5

                fig.add_trace(
                    go.Mesh3d(
                        x=[x0, x1, x1, x0, x0, x1, x1, x0],
                        y=[y0, y0, y1, y1, y0, y0, y1, y1],
                        z=[z0, z0, z0, z0, z1, z1, z1, z1],
                        i=[7, 0, 0, 0, 4, 4, 6, 1, 4, 0, 3, 6],
                        j=[3, 4, 1, 2, 5, 6, 5, 2, 7, 1, 6, 3],
                        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 2],
                        color=f"rgb({int(30 + 180*intensity)}, "
                              f"{int(50 + 100*(1-intensity))}, "
                              f"{int(200 - 150*intensity)})",
                        opacity=0.85,
                        hovertext=f"ρ = {val:.4f}<br>셀 ({i},{j},{k})",
                        hoverinfo="text",
                        showscale=False,
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
    )

    if save_path is None:
        save_path = Path(OUTPUT_DIR) / "rho_density.html"
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(save_path))

    if show:
        fig.show()

    return fig
