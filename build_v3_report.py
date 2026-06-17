"""변인 통제 v3 결과를 보고서용 한 페이지 HTML로 생성."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from config import (
    DROP_HEIGHT,
    FRICTION,
    MAX_ANGULAR_VEL,
    OUTPUT_DIR,
    RESTITUTION,
)
from simulation.charts import plot_runs_comparison, prob_y_axes_by_study
from simulation.dashboard import collect_runs
from simulation.output_layout import (
    CONTROLLED_GROUP_PRESETS,
    STUDY_CONTROLLED_V3,
    STUDY_LABELS,
    comparison_html_path,
    png_export_path,
)
from simulation.plotly_export import try_write_png_export
from simulation.run_descriptions import preset_display_label_ko, variable_group_header_ko

DOCS_REPORT = Path("docs/controlled_v3_report.html")


def _png_flat(group: str, preset: str, chart: str) -> str:
    return f"studies__controlled_v3__{group}__runs__{preset}__{chart}.png"


def _load_results(run_dir: Path) -> dict | None:
    path = run_dir / "results.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _prob_summary(probs: dict) -> str:
    p2 = float(probs.get("2", probs.get(2, 0)))
    p5 = float(probs.get("5", probs.get(5, 0)))
    return f"2번 {p2*100:.2f}% · 5번 {p5*100:.2f}%"


def _ensure_comparison_png(output_dir: Path, runs: list[dict]) -> str:
    """10개 시뮬 비교 차트 PNG 생성."""
    from simulation.output_layout import STUDY_PRESETS

    comp_html = comparison_html_path(STUDY_CONTROLLED_V3, output_dir)
    study_runs = [r for r in runs if r.get("study_id") == STUDY_CONTROLLED_V3]
    order = {n: i for i, n in enumerate(STUDY_PRESETS[STUDY_CONTROLLED_V3])}
    study_runs.sort(key=lambda r: order.get(r["rho_name"], 999))

    axes = prob_y_axes_by_study(output_dir).get(STUDY_CONTROLLED_V3)
    label = STUDY_LABELS[STUDY_CONTROLLED_V3]
    fig = plot_runs_comparison(
        study_runs,
        comp_html,
        title=("바닥의 눈 확률 분포 비교", f"{label} — {len(study_runs)}개 시뮬레이션"),
        y_range=axes[0] if axes else None,
        y_dtick=axes[1] if axes else None,
    )
    try_write_png_export(fig, comp_html, png_kw=dict(width=1400, height=420, scale=2))
    return png_export_path(comp_html, output_dir).name


def _analysis_paragraphs() -> list[str]:
    return [
        "균일 밀도(ρ=1)는 6면 모두 약 16.7%로 이론값 1/6과 일치하며, 시뮬 파이프라인의 기준선으로 쓸 수 있다.",
        "밀도 배율(ρ) 변인: ρ=3에서는 2번이 약간 높고, ρ=4·5로 갈수록 2번은 낮아지고 5번은 높아진다. "
        "+x 쪽 질량 편심에서 동역학적으로 5번(−x 바닥) 우세가 커지는 패턴이다.",
        "반지름 변인: r=0.20·0.22에서 2번·5번 편향 방향이 달라진다. r=0.22는 2번이 가장 높고 5번이 가장 낮다 — "
        "같은 x₀에서도 관성·토크 구조가 바뀌면 최종 면 분포가 뒤집힐 수 있음을 보여 준다.",
        "편심 x좌표 변인: x₀가 커질수록 5번 확률이 소폭 증가하고 2번은 감소한다. "
        "무거운 구가 +x로 멀어질수록 x축 면(2·5) 편향이 강해진다.",
    ]


def build_report(output_dir: str | Path = OUTPUT_DIR) -> Path:
    output_dir = Path(output_dir)
    png_rel = "../output/png"
    study_label = STUDY_LABELS[STUDY_CONTROLLED_V3]
    runs = collect_runs(output_dir)
    comp_png = _ensure_comparison_png(output_dir, runs)

    cards: list[str] = []
    for group, presets in CONTROLLED_GROUP_PRESETS.items():
        for preset in presets:
            run_dir = output_dir / "studies" / STUDY_CONTROLLED_V3 / group / "runs" / preset
            data = _load_results(run_dir)
            label = preset_display_label_ko(preset)
            summary = _prob_summary(data["probabilities"]) if data else "결과 없음"
            dens = _png_flat(group, preset, "rho_density")
            prob = _png_flat(group, preset, "face_probabilities")
            cards.append(
                f"""<article class="card" id="{escape(preset)}">
  <h3>{escape(label)}</h3>
  <p class="stat">{escape(summary)}</p>
  <img src="{png_rel}/{escape(dens)}" alt="{escape(label)} 질량분포" loading="lazy" />
  <img src="{png_rel}/{escape(prob)}" alt="{escape(label)} 확률분포" loading="lazy" />
</article>"""
            )

    group_notes = " · ".join(
        variable_group_header_ko(STUDY_CONTROLLED_V3, g) for g in CONTROLLED_GROUP_PRESETS
    )
    analysis = "".join(f"<li>{escape(p)}</li>" for p in _analysis_paragraphs())

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(study_label)} — 보고서용 결과 한눈에</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #1e293b;
      --text: #f1f5f9;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --border: #334155;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ height: 100%; overflow: hidden; background: var(--bg); color: var(--text); }}
    .page {{
      height: 100vh;
      display: grid;
      grid-template-rows: auto auto auto 1fr;
      gap: 6px;
      padding: 8px 10px 10px;
      font-family: "Pretendard", "Malgun Gothic", sans-serif;
    }}
    header {{
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: 8px 16px;
      font-size: 0.72rem;
      line-height: 1.35;
      color: var(--muted);
    }}
    header h1 {{
      font-size: 1rem;
      color: var(--text);
      margin-right: auto;
    }}
    .analysis {{
      font-size: 0.68rem;
      line-height: 1.4;
      color: var(--muted);
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px 12px;
      max-height: 4.2em;
      overflow: hidden;
    }}
    .analysis ul {{ list-style: none; padding: 0; }}
    .analysis li::before {{ content: "• "; color: var(--accent); }}
    .comparison {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 4px;
      min-height: 0;
    }}
    .comparison img {{
      width: 100%;
      height: 18vh;
      object-fit: contain;
      display: block;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      grid-template-rows: repeat(2, 1fr);
      gap: 6px;
      min-height: 0;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 4px 6px;
      display: grid;
      grid-template-rows: auto auto 1fr 1fr;
      gap: 2px;
      min-height: 0;
      overflow: hidden;
    }}
    .card h3 {{
      font-size: 0.72rem;
      font-weight: 600;
      color: var(--accent);
    }}
    .card .stat {{
      font-size: 0.6rem;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .card img {{
      width: 100%;
      height: 100%;
      min-height: 0;
      object-fit: contain;
      background: #fff;
      border-radius: 3px;
    }}
    @media (max-width: 1100px) {{
      html, body {{ overflow: auto; height: auto; }}
      .page {{ height: auto; min-height: 100vh; }}
      .grid {{ grid-template-columns: repeat(2, 1fr); grid-template-rows: auto; }}
      .analysis {{ grid-template-columns: 1fr; max-height: none; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header>
      <h1>{escape(study_label)} — 시뮬레이션 결과 (N=100,000)</h1>
      <span>H={DROP_HEIGHT} m · e={RESTITUTION} · μ={FRICTION} · ω≤{MAX_ANGULAR_VEL} rad/s</span>
      <span>변인 그룹: {escape(group_notes)}</span>
    </header>
    <section class="analysis" aria-label="핵심 해석">
      <ul>{analysis}</ul>
    </section>
    <section class="comparison" aria-label="10개 시뮬 비교">
      <img src="{png_rel}/{escape(comp_png)}" alt="10개 프리셋 확률 비교" />
    </section>
    <section class="grid" aria-label="프리셋별 차트">
      {"".join(cards)}
    </section>
  </div>
</body>
</html>
"""
    DOCS_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_REPORT.write_text(html, encoding="utf-8")
    return DOCS_REPORT


def main() -> None:
    path = build_report()
    print(f"보고서 HTML: {path.resolve()}")


if __name__ == "__main__":
    main()
