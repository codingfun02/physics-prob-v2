"""차트 2줄 제목 — Plotly title/subtitle (PNG·HTML 모두 안정적)."""

from __future__ import annotations

from config import (
    CHART_TITLE_LINE_GAP,
    CHART_TITLE_MAIN_SIZE,
    CHART_TITLE_MARGIN_TOP,
    CHART_TITLE_SUB_SIZE,
    CHART_TITLE_TOP_PAD,
)

_TITLE_COLOR = "#0f172a"


def apply_two_line_title(
    fig,
    line1: str,
    line2: str | None = None,
    *,
    margin_top: int | None = None,
) -> None:
    """Plotly figure에 2줄 제목 적용."""
    t = margin_top if margin_top is not None else CHART_TITLE_MARGIN_TOP

    margin = fig.layout.margin
    margin_patch: dict = {"t": t}
    if margin:
        for side in ("b", "l", "r"):
            val = getattr(margin, side, None)
            if val is not None:
                margin_patch[side] = val

    title_dict: dict = {
        "text": f"<b>{line1}</b>",
        "x": 0.5,
        "xanchor": "center",
        "font": dict(size=CHART_TITLE_MAIN_SIZE, color=_TITLE_COLOR),
        "pad": dict(t=CHART_TITLE_TOP_PAD, b=CHART_TITLE_LINE_GAP),
    }
    if line2:
        title_dict["subtitle"] = dict(
            text=line2,
            font=dict(size=CHART_TITLE_SUB_SIZE, color=_TITLE_COLOR),
        )

    existing = list(fig.layout.annotations or ())
    data_anns = [
        a
        for a in existing
        if not (a.xref == "paper" and a.yref == "paper" and a.y == 1)
    ]

    fig.update_layout(
        title=title_dict,
        annotations=data_anns,
        margin=margin_patch,
    )
