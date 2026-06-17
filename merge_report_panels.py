"""보고서용 — 같은 변인 그룹의 확률·질량 PNG를 3×2 패널로 병합."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from config import OUTPUT_DIR, PNG_EXPORT_SUBDIR
from simulation.output_layout import (
    CONTROLLED_GROUP_PRESETS,
    STUDY_CONTROLLED,
    STUDY_CONTROLLED_V3,
    STUDY_LABELS,
)
from simulation.run_descriptions import preset_display_label_ko, variable_group_header_ko

PROB_CHART = "face_probabilities"
DENSITY_CHART = "rho_density"
REPORT_PANELS_DIR = Path("docs/report_panels")


def _chart_png(
    png_dir: Path,
    study_id: str,
    group: str,
    preset: str,
    chart: str,
) -> Path:
    return png_dir / f"studies__{study_id}__{group}__runs__{preset}__{chart}.png"


def _merged_name(study_id: str, group: str) -> str:
    return f"merged__{study_id}__{group}.png"


def _resize_to_width(img: Image.Image, width: int) -> Image.Image:
    if img.width == width:
        return img
    height = round(img.height * width / img.width)
    return img.resize((width, height), Image.Resampling.LANCZOS)


def _load_chart(
    png_dir: Path,
    study_id: str,
    group: str,
    preset: str,
    chart: str,
    cell_width: int,
) -> Image.Image:
    path = _chart_png(png_dir, study_id, group, preset, chart)
    if not path.exists():
        raise FileNotFoundError(path)
    return _resize_to_width(Image.open(path).convert("RGB"), cell_width)


def merge_uniform_panel(
    study_id: str,
    png_dir: Path,
    *,
    cell_width: int = 1200,
    gap: int = 16,
    bg: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """1×2 — 왼쪽 확률, 오른쪽 질량 (uniform)."""
    preset = "uniform"
    group = "uniform"
    prob = _load_chart(png_dir, study_id, group, preset, PROB_CHART, cell_width)
    dens = _load_chart(png_dir, study_id, group, preset, DENSITY_CHART, cell_width)

    cell_h = max(prob.height, dens.height)
    panel_w = 2 * cell_width + gap
    canvas = Image.new("RGB", (panel_w, cell_h), bg)

    for col, img in enumerate((prob, dens)):
        x = col * (cell_width + gap)
        y = (cell_h - img.height) // 2
        canvas.paste(img, (x, y))
    return canvas


def merge_variable_group_panel(
    study_id: str,
    group: str,
    presets: list[str],
    png_dir: Path,
    *,
    cell_width: int = 1200,
    gap: int = 16,
    bg: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """위: 확률 3개, 아래: 대응 질량 3개."""
    if len(presets) != 3:
        raise ValueError(f"{group}: 프리셋 3개 필요 (현재 {len(presets)}개)")

    prob_row: list[Image.Image] = []
    dens_row: list[Image.Image] = []
    for preset in presets:
        prob_row.append(_load_chart(png_dir, study_id, group, preset, PROB_CHART, cell_width))
        dens_row.append(_load_chart(png_dir, study_id, group, preset, DENSITY_CHART, cell_width))

    cell_h = max(im.height for im in prob_row + dens_row)
    cols = 3
    panel_w = cols * cell_width + (cols - 1) * gap
    panel_h = 2 * cell_h + gap

    canvas = Image.new("RGB", (panel_w, panel_h), bg)

    def _paste_row(images: list[Image.Image], y: int) -> None:
        for col, img in enumerate(images):
            x = col * (cell_width + gap)
            # 세로 중앙 정렬 (높이 차이 흡수)
            offset_y = y + (cell_h - img.height) // 2
            canvas.paste(img, (x, offset_y))

    _paste_row(prob_row, 0)
    _paste_row(dens_row, cell_h + gap)
    return canvas


def build_panels(
    study_id: str,
    output_dir: str | Path = OUTPUT_DIR,
    *,
    cell_width: int = 1200,
    gap: int = 16,
    copy_to_docs: bool = True,
) -> list[Path]:
    png_dir = Path(output_dir) / PNG_EXPORT_SUBDIR
    if not png_dir.is_dir():
        raise FileNotFoundError(f"PNG 폴더 없음: {png_dir}")

    written: list[Path] = []
    docs_dir = REPORT_PANELS_DIR
    if copy_to_docs:
        docs_dir.mkdir(parents=True, exist_ok=True)

    def _save_panel(panel: Image.Image, group: str) -> None:
        out_name = _merged_name(study_id, group)
        out_path = png_dir / out_name
        panel.save(out_path, format="PNG", optimize=True)
        written.append(out_path)
        if copy_to_docs:
            doc_path = docs_dir / out_name
            panel.save(doc_path, format="PNG", optimize=True)
            written.append(doc_path)

    # uniform: 1×2 (확률 | 질량)
    panel = merge_uniform_panel(
        study_id,
        png_dir,
        cell_width=cell_width,
        gap=gap,
    )
    _save_panel(panel, "uniform")

    # factor / radius / center: 3×2
    for group, presets in CONTROLLED_GROUP_PRESETS.items():
        if group == "uniform" or len(presets) != 3:
            continue
        panel = merge_variable_group_panel(
            study_id,
            group,
            presets,
            png_dir,
            cell_width=cell_width,
            gap=gap,
        )
        _save_panel(panel, group)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="변인 그룹별 확률·질량 PNG 3×2 병합")
    parser.add_argument(
        "--study",
        default=STUDY_CONTROLLED_V3,
        choices=[STUDY_CONTROLLED, STUDY_CONTROLLED_V3],
        help="대상 실험 묶음",
    )
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--cell-width", type=int, default=1200, help="열당 픽셀 너비")
    parser.add_argument("--gap", type=int, default=16, help="셀 사이 간격(px)")
    parser.add_argument(
        "--no-docs-copy",
        action="store_true",
        help="docs/report_panels/ 복사 생략",
    )
    args = parser.parse_args()

    label = STUDY_LABELS[args.study]
    paths = build_panels(
        args.study,
        args.output_dir,
        cell_width=args.cell_width,
        gap=args.gap,
        copy_to_docs=not args.no_docs_copy,
    )

    print(f"{label} — 병합 패널 {len(paths) // (1 if args.no_docs_copy else 2)}개")

    header = variable_group_header_ko(args.study, "uniform")
    print(f"  [uniform] {header}")
    print("       왼쪽: 확률 (ρ=1)  |  오른쪽: 질량 (ρ=1)")
    print(f"       → {_merged_name(args.study, 'uniform')}")

    for group in ("factor", "radius", "center"):
        header = variable_group_header_ko(args.study, group)
        presets = CONTROLLED_GROUP_PRESETS[group]
        cols = ", ".join(preset_display_label_ko(p) for p in presets)
        print(f"  [{group}] {header}")
        print(f"       위: 확률 ({cols})")
        print(f"       아래: 질량 ({cols})")
        print(f"       → {_merged_name(args.study, group)}")


if __name__ == "__main__":
    main()
