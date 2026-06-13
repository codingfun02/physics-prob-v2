"""확률분포 Plotly 차트."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go

from config import (
    CHART_TITLE_MARGIN_TOP,
    OUTPUT_DIR,
    PROB_EXPORT_AXIS_TICK_SIZE,
    PROB_EXPORT_AXIS_TITLE_SIZE,
    PROB_EXPORT_BAR_LABEL_SIZE,
    PROB_EXPORT_FONT_SIZE,
    PROB_EXPORT_LEGEND_SIZE,
    PROB_EXPORT_MARGIN,
    PROB_EXPORT_PNG_KW,
    PROB_EXPORT_TITLE_MARGIN_TOP,
    PROB_HTML_LEGEND,
    PROB_HTML_MARGIN,
)
from simulation.chart_palette import (
    AXIS,
    COMPARISON_COLORS,
    GRAY_BLUE_DARK,
    GRID,
    PROB_BAR_FACE_COLORS,
    PROB_ERROR_COLOR,
    PROB_REF_LINE,
    TEXT,
)
from simulation.chart_title import apply_two_line_title
from simulation.run_descriptions import preset_display_label_ko
from simulation.plotly_export import try_write_png_export, write_plotly_html

_PROB_BAR_LABEL_SIZE = 17
_PROB_AXIS_TITLE_SIZE = 15
_PROB_AXIS_TICK_SIZE = 14


def _prep_prob_png_export(fig: go.Figure) -> None:
    """PNG 저장 시 보고서용 조밀 레이아웃 (config.py PROB_EXPORT_*)."""
    fig.update_layout(
        autosize=False,
        margin={**PROB_EXPORT_MARGIN, "t": PROB_EXPORT_TITLE_MARGIN_TOP},
        font=dict(size=PROB_EXPORT_FONT_SIZE),
        legend=dict(font=dict(size=PROB_EXPORT_LEGEND_SIZE)),
        bargap=0.24,
    )
    fig.update_xaxes(
        title_font=dict(size=PROB_EXPORT_AXIS_TITLE_SIZE),
        tickfont=dict(size=PROB_EXPORT_AXIS_TICK_SIZE),
    )
    fig.update_yaxes(
        title_font=dict(size=PROB_EXPORT_AXIS_TITLE_SIZE),
        tickfont=dict(size=PROB_EXPORT_AXIS_TICK_SIZE),
    )
    fig.update_traces(
        textfont=dict(size=PROB_EXPORT_BAR_LABEL_SIZE),
        selector=dict(type="scatter", mode="text"),
    )
    for ann in fig.layout.annotations or ():
        if ann.font:
            ann.font.size = PROB_EXPORT_LEGEND_SIZE


_REPORT_LAYOUT = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color=TEXT, size=12, family="Arial, Helvetica, sans-serif"),
)
_REPORT_XAXIS = dict(
    tickmode="linear",
    dtick=1,
    showgrid=False,
    linecolor=AXIS,
    tickcolor=AXIS,
    zeroline=False,
)
_REPORT_YAXIS = dict(
    tickformat=".1%",
    showgrid=True,
    gridcolor=GRID,
    gridwidth=1,
    linecolor=AXIS,
    tickcolor=AXIS,
    zeroline=False,
)


def _prob_value(probabilities: dict, face: int) -> float:
    if not probabilities:
        return 0.0
    return float(probabilities.get(str(face), probabilities.get(face, 0.0)))


def _prob_y_range(p: list[float], err: list[float], uniform_p: float) -> list[float]:
    """데이터·오차막대·막대 라벨(오차 위)을 고려한 y축 범위."""
    err_max = max(err) if err else 0.0
    p_min = min(p) if p else uniform_p
    p_max = max(p) if p else uniform_p
    y_lo = max(0.0, min(p_min - err_max, uniform_p) - 0.006)
    y_hi = max(p_max + err_max + 0.018, uniform_p + 0.008)
    return [y_lo, y_hi + 0.004]


def _prob_bar_label_offset(y_range: list[float]) -> float:
    return (y_range[1] - y_range[0]) * 0.02


def _prob_bar_label_trace(
    faces: list[int],
    p: list[float],
    err: list[float],
    labels: list[str],
    y_range: list[float],
) -> go.Scatter:
    """오차막대 위에 확률 % 라벨."""
    offset = _prob_bar_label_offset(y_range)
    return go.Scatter(
        x=faces,
        y=[pi + ei + offset for pi, ei in zip(p, err)],
        text=labels,
        mode="text",
        textfont=dict(
            size=_PROB_BAR_LABEL_SIZE,
            color=TEXT,
            family="Arial, Helvetica, sans-serif",
        ),
        showlegend=False,
        hoverinfo="skip",
    )


def prob_series(probs: dict[int, float], n_trials: int) -> tuple[list[float], list[float]]:
    """막대 높이·표준오차 리스트."""
    faces = list(range(1, 7))
    p = [_prob_value(probs, f) for f in faces]
    err = [
        ((p_i * (1 - p_i) / n_trials) ** 0.5) if n_trials > 0 else 0.0 for p_i in p
    ]
    return p, err


def _nice_prob_dtick(span: float) -> float:
    """확률(비율) 축 눈금 간격."""
    if span <= 0.022:
        return 0.002
    if span <= 0.045:
        return 0.005
    if span <= 0.09:
        return 0.01
    return 0.015


def unify_prob_y_axis(
    series_list: list[tuple[list[float], list[float]]],
) -> tuple[list[float], float]:
    """여러 시뮬레이션을 아우르는 y축 범위·dtick."""
    uniform_p = 1 / 6
    if not series_list:
        return [0.14, 0.20], 0.01
    y_lo, y_hi = 1.0, 0.0
    for p, err in series_list:
        lo, hi = _prob_y_range(p, err, uniform_p)
        y_lo = min(y_lo, lo)
        y_hi = max(y_hi, hi)
    dtick = _nice_prob_dtick(y_hi - y_lo)
    y_lo = max(0.0, math.floor(y_lo / dtick - 1e-9) * dtick)
    y_hi = math.ceil(y_hi / dtick - 1e-9) * dtick
    return [y_lo, y_hi], dtick


def variable_group_from_results(data: dict) -> str:
    from simulation.output_layout import variable_group_for_preset

    extra = data.get("extra") or {}
    study_id = extra.get("study_id")
    return variable_group_for_preset(data["rho_name"], study_id) or "misc"


def study_from_results(data: dict) -> str:
    from simulation.output_layout import study_for_preset

    extra = data.get("extra") or {}
    study_id = extra.get("study_id")
    if study_id:
        return study_id
    inferred = study_for_preset(data.get("rho_name", ""))
    return inferred or "misc"


def prob_y_axes_by_study(
    output_dir: str | Path = OUTPUT_DIR,
) -> dict[str, tuple[list[float], float]]:
    """output/runs 기준 실험(study)별 통일 y축."""
    output_dir = Path(output_dir)
    studies: dict[str, list[tuple[list[float], list[float]]]] = defaultdict(list)
    runs_root = output_dir / "runs"
    if runs_root.is_dir():
        for results_path in sorted(runs_root.glob("*/results.json")):
            data = json.loads(results_path.read_text(encoding="utf-8"))
            probs = {int(k): float(v) for k, v in data["probabilities"].items()}
            n_trials = int(data["n_trials"])
            sid = study_from_results(data)
            studies[sid].append(prob_series(probs, n_trials))
    return {sid: unify_prob_y_axis(series) for sid, series in studies.items()}


def prob_y_axis_for_study(
    output_dir: str | Path,
    study_id: str,
    *,
    extra: list[tuple[dict[int, float], int]] | None = None,
) -> tuple[list[float], float]:
    """한 실험(study) y축 (디스크 run + extra 시리즈 포함)."""
    output_dir = Path(output_dir)
    series_list: list[tuple[list[float], list[float]]] = []
    runs_root = output_dir / "runs"
    if runs_root.is_dir():
        for results_path in sorted(runs_root.glob("*/results.json")):
            data = json.loads(results_path.read_text(encoding="utf-8"))
            if study_from_results(data) != study_id:
                continue
            probs = {int(k): float(v) for k, v in data["probabilities"].items()}
            series_list.append(prob_series(probs, int(data["n_trials"])))
    if extra:
        for probs, n_trials in extra:
            series_list.append(prob_series(probs, n_trials))
    return unify_prob_y_axis(series_list)


def prob_y_axes_by_variable_group(
    output_dir: str | Path = OUTPUT_DIR,
) -> dict[str, tuple[list[float], float]]:
    """output/runs 기준 변인 그룹별 통일 y축."""
    output_dir = Path(output_dir)
    groups: dict[str, list[tuple[list[float], list[float]]]] = defaultdict(list)
    runs_root = output_dir / "runs"
    if runs_root.is_dir():
        for results_path in sorted(runs_root.glob("*/results.json")):
            data = json.loads(results_path.read_text(encoding="utf-8"))
            probs = {int(k): float(v) for k, v in data["probabilities"].items()}
            n_trials = int(data["n_trials"])
            vg = variable_group_from_results(data)
            groups[vg].append(prob_series(probs, n_trials))
    return {vg: unify_prob_y_axis(series) for vg, series in groups.items()}


def prob_y_axis_for_variable_group(
    output_dir: str | Path,
    variable_group: str,
    *,
    extra: list[tuple[dict[int, float], int]] | None = None,
) -> tuple[list[float], float]:
    """한 변인 그룹 y축 (디스크 run + extra 시리즈 포함)."""
    output_dir = Path(output_dir)
    series_list: list[tuple[list[float], list[float]]] = []
    runs_root = output_dir / "runs"
    if runs_root.is_dir():
        for results_path in sorted(runs_root.glob("*/results.json")):
            data = json.loads(results_path.read_text(encoding="utf-8"))
            if variable_group_from_results(data) != variable_group:
                continue
            probs = {int(k): float(v) for k, v in data["probabilities"].items()}
            series_list.append(prob_series(probs, int(data["n_trials"])))
    if extra:
        for probs, n_trials in extra:
            series_list.append(prob_series(probs, n_trials))
    return unify_prob_y_axis(series_list)


def plot_probabilities(
    probs: dict[int, float],
    n_trials: int,
    title: str | tuple[str, str | None],
    save_path: str | Path,
    *,
    y_range: list[float] | None = None,
    y_dtick: float | None = None,
) -> go.Figure:
    """바닥의 눈 확률 막대그래프 — 보고서용 균일 스타일."""
    if isinstance(title, tuple):
        line1, line2 = title
    else:
        line1, line2 = str(title), None
    faces = list(range(1, 7))
    p, err = prob_series(probs, n_trials)
    labels = [f"{v * 100:.2f}%" for v in p]
    uniform_p = 1 / 6

    if y_range is None or y_dtick is None:
        auto_range, auto_dtick = unify_prob_y_axis([(p, err)])
        y_range = y_range if y_range is not None else auto_range
        y_dtick = y_dtick if y_dtick is not None else auto_dtick

    yaxis_cfg = dict(
        title=dict(text="확률", font=dict(size=_PROB_AXIS_TITLE_SIZE)),
        tickfont=dict(size=_PROB_AXIS_TICK_SIZE),
        range=y_range,
        tickmode="linear",
        dtick=y_dtick,
        **_REPORT_YAXIS,
    )

    fig = go.Figure(
        data=[
            go.Bar(
                x=faces,
                y=p,
                marker=dict(
                    color=PROB_BAR_FACE_COLORS,
                    line=dict(width=0),
                ),
                error_y=dict(
                    type="data",
                    array=err,
                    arrayminus=err,
                    color=PROB_ERROR_COLOR,
                    thickness=1.2,
                    width=3,
                ),
                name="확률",
                hovertemplate=(
                    "바닥의 눈 %{x}<br>확률: %{y:.4f} (%{y:.2%})<extra></extra>"
                ),
            ),
            _prob_bar_label_trace(faces, p, err, labels, y_range),
            go.Scatter(
                x=[0.4, 6.6],
                y=[uniform_p, uniform_p],
                mode="lines",
                line=dict(color=PROB_REF_LINE, dash="dash", width=1.5),
                name="균일 (1/6)",
                hovertemplate="균일 확률: 16.67%<extra></extra>",
            ),
        ]
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color=TEXT, size=13, family="Arial, Helvetica, sans-serif"),
        xaxis=dict(
            title=dict(text="바닥의 눈", font=dict(size=_PROB_AXIS_TITLE_SIZE)),
            tickfont=dict(size=_PROB_AXIS_TICK_SIZE),
            range=[0.3, 6.7],
            **_REPORT_XAXIS,
        ),
        yaxis=yaxis_cfg,
        bargap=0.28,
        legend=dict(
            bgcolor="rgba(255, 255, 255, 0.92)",
            bordercolor=AXIS,
            borderwidth=1,
            font=dict(size=13),
            **PROB_HTML_LEGEND,
        ),
        margin=PROB_HTML_MARGIN,
    )
    apply_two_line_title(fig, line1, line2)
    write_plotly_html(fig, save_path, chart_kind="probability")
    try_write_png_export(
        fig,
        save_path,
        prep=_prep_prob_png_export,
        png_kw=PROB_EXPORT_PNG_KW,
    )
    return fig


def plot_runs_comparison(
    runs: list[dict],
    save_path: str | Path,
    title: str | tuple[str, str | None] = (
        "바닥의 눈 확률 분포 비교",
        "변인 통제 v2",
    ),
    *,
    y_range: list[float] | None = None,
    y_dtick: float | None = None,
) -> go.Figure:
    """여러 실행의 면별 확률을 나란히 막대그래프로 비교."""
    if not runs:
        raise ValueError("비교할 실행이 없습니다.")

    if isinstance(title, tuple):
        line1, line2 = title
    else:
        line1, line2 = str(title), None

    faces = list(range(1, 7))
    bar_traces: list[go.Bar] = []
    for i, run in enumerate(runs):
        probs = [_prob_value(run.get("probabilities", {}), f) for f in faces]
        rho_name = run.get("rho_name", run.get("run_id", f"run{i}"))
        label = preset_display_label_ko(rho_name)
        color = COMPARISON_COLORS[i % len(COMPARISON_COLORS)]
        bar_traces.append(
            go.Bar(
                name=label,
                x=faces,
                y=probs,
                marker=dict(color=color, line=dict(width=0)),
                opacity=0.92,
                legendgroup=label,
                hovertemplate=f"{label}<br>눈 %{{x}}: %{{y:.2%}}<extra></extra>",
            )
        )

    uniform_p = 1 / 6

    if y_range is None or y_dtick is None:
        series = [
            prob_series(
                {int(k): float(v) for k, v in r.get("probabilities", {}).items()},
                int(r.get("n_trials", 0) or 1),
            )
            for r in runs
        ]
        auto_range, auto_dtick = unify_prob_y_axis(series)
        y_range = y_range if y_range is not None else auto_range
        y_dtick = y_dtick if y_dtick is not None else auto_dtick

    ref_line = go.Scatter(
        x=[0.4, 6.6],
        y=[uniform_p, uniform_p],
        mode="lines",
        name="균일 (1/6)",
        line=dict(color=PROB_REF_LINE, dash="dash", width=1.5),
        hovertemplate="균일 확률: 16.67%<extra></extra>",
    )

    fig = go.Figure(data=[*bar_traces, ref_line])
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color=TEXT, size=13, family="Arial, Helvetica, sans-serif"),
        xaxis=dict(
            title=dict(text="바닥의 눈", font=dict(size=_PROB_AXIS_TITLE_SIZE)),
            tickfont=dict(size=_PROB_AXIS_TICK_SIZE),
            range=[0.3, 6.7],
            dtick=1,
            showgrid=False,
            linecolor=AXIS,
            tickcolor=AXIS,
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="확률", font=dict(size=_PROB_AXIS_TITLE_SIZE)),
            tickfont=dict(size=_PROB_AXIS_TICK_SIZE),
            range=y_range,
            tickmode="linear",
            dtick=y_dtick,
            tickformat=".1%",
            showgrid=True,
            gridcolor=GRID,
            gridwidth=1,
            linecolor=AXIS,
            tickcolor=AXIS,
            zeroline=False,
        ),
        barmode="group",
        bargap=0.22,
        bargroupgap=0.08,
        legend=dict(
            orientation="v",
            x=1.02,
            y=1.0,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255, 255, 255, 0.95)",
            bordercolor=AXIS,
            borderwidth=1,
            font=dict(size=12),
            tracegroupgap=4,
        ),
        margin=dict(t=CHART_TITLE_MARGIN_TOP, b=72, l=72, r=200),
        autosize=True,
    )
    apply_two_line_title(fig, line1, line2)
    write_plotly_html(fig, save_path, chart_kind="comparison")
    return fig
