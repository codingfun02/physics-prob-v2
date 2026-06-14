"""output/ 디렉터리 레이아웃 — 모든 저장 경로의 단일 정의."""

from __future__ import annotations

import shutil
from pathlib import Path

from config import ARCHIVE_STUDIES_DIR, OUTPUT_DIR, PNG_EXPORT_SUBDIR
from density.analytic import (
    CONTROLLED_STUDY_NAMES,
    CONTROLLED_STUDY_SIM_NAMES,
    CONTROLLED_STUDY_SPECS,
    RHO_SCAN_SIM_NAMES,
    RHO_SCAN_SPECS,
    SPHERE_STUDY_SIM_NAMES,
    lookup_controlled_spec,
)

# 실험 묶음 ID
STUDY_SPHERE_LEGACY = "sphere_legacy"
STUDY_CONTROLLED = "controlled"
STUDY_CONTROLLED_V3 = "controlled_v3"
STUDY_RHO_SCAN = "rho_scan"

STUDY_PRESETS: dict[str, list[str]] = {
    STUDY_RHO_SCAN: list(RHO_SCAN_SIM_NAMES),
    STUDY_CONTROLLED: list(CONTROLLED_STUDY_SIM_NAMES),
    STUDY_CONTROLLED_V3: list(CONTROLLED_STUDY_SIM_NAMES),
    STUDY_SPHERE_LEGACY: list(SPHERE_STUDY_SIM_NAMES),
}

STUDY_LABELS: dict[str, str] = {
    STUDY_RHO_SCAN: "1단계 — ρ 스캔",
    STUDY_CONTROLLED: "변인 통제 v2",
    STUDY_CONTROLLED_V3: "변인 통제 v3-높이/반발 변경",
    STUDY_SPHERE_LEGACY: "구 밀도 실험",
}

# 변인 그룹 (대시보드·폴더 구조)
VARIABLE_GROUP_ORDER = ["uniform", "factor", "radius", "center"]

CONTROLLED_GROUP_PRESETS: dict[str, list[str]] = {
    "uniform": ["uniform"],
    "factor": [n for n in CONTROLLED_STUDY_NAMES if n.startswith("ctrl_factor_")],
    "radius": [n for n in CONTROLLED_STUDY_NAMES if n.startswith("ctrl_radius_")],
    "center": [n for n in CONTROLLED_STUDY_NAMES if n.startswith("ctrl_center_")],
}

RHO_SCAN_GROUP_PRESETS: dict[str, list[str]] = {
    "factor": list(RHO_SCAN_SIM_NAMES),
}

STUDY_VARIABLE_GROUPS: dict[str, dict[str, list[str]]] = {
    STUDY_RHO_SCAN: RHO_SCAN_GROUP_PRESETS,
    STUDY_CONTROLLED: CONTROLLED_GROUP_PRESETS,
    STUDY_CONTROLLED_V3: CONTROLLED_GROUP_PRESETS,
    STUDY_SPHERE_LEGACY: {"legacy": list(SPHERE_STUDY_SIM_NAMES)},
}

# 대시보드·PNG export·refresh 대상 (ρ 스캔·구 밀도 실험 제외)
ARCHIVED_STUDY_IDS: frozenset[str] = frozenset({STUDY_RHO_SCAN, STUDY_SPHERE_LEGACY})
DASHBOARD_STUDY_IDS: list[str] = [STUDY_CONTROLLED, STUDY_CONTROLLED_V3]

# 이전 경로 (마이그레이션용)
_LEGACY_STUDY_DIRS = {
    STUDY_SPHERE_LEGACY: "sphere_study",
    STUDY_CONTROLLED: "controlled_study",
    STUDY_CONTROLLED_V3: "controlled_study_v3",
}


def output_root(output_dir: str | Path = OUTPUT_DIR) -> Path:
    return Path(output_dir)


def runs_dir(output_dir: str | Path = OUTPUT_DIR) -> Path:
    """레거시 flat runs/ (이전 시뮬)."""
    return output_root(output_dir) / "runs"


def studies_dir(output_dir: str | Path = OUTPUT_DIR) -> Path:
    return output_root(output_dir) / "studies"


def study_dir(study_id: str, output_dir: str | Path = OUTPUT_DIR) -> Path:
    return studies_dir(output_dir) / study_id


def variable_group_dir(
    study_id: str,
    variable_group: str,
    output_dir: str | Path = OUTPUT_DIR,
) -> Path:
    return study_dir(study_id, output_dir) / variable_group


def grouped_run_dir(
    study_id: str,
    variable_group: str,
    preset_name: str,
    output_dir: str | Path = OUTPUT_DIR,
) -> Path:
    """studies/{study}/{group}/runs/{preset}/"""
    return variable_group_dir(study_id, variable_group, output_dir) / "runs" / preset_name


def density_previews_dir(study_id: str, output_dir: str | Path = OUTPUT_DIR) -> Path:
    return study_dir(study_id, output_dir) / "density_previews"


def density_preview_path(
    study_id: str,
    index: int,
    preset_name: str,
    output_dir: str | Path = OUTPUT_DIR,
) -> Path:
    return density_previews_dir(study_id, output_dir) / f"{index:02d}_{preset_name}.html"


def adhoc_preview_path(rho_label: str, output_dir: str | Path = OUTPUT_DIR) -> Path:
    """단일 프리셋 미리보기 (실험 묶음 밖)."""
    return output_root(output_dir) / "previews" / f"{rho_label}.html"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def archive_studies_root() -> Path:
    return project_root() / ARCHIVE_STUDIES_DIR


def archive_legacy_study_outputs(output_dir: str | Path = OUTPUT_DIR) -> int:
    """ρ 스캔·구 밀도 실험 데이터를 archive_studies/ 로 이동."""
    out = output_root(output_dir)
    archive = archive_studies_root()
    archive.mkdir(parents=True, exist_ok=True)
    moved = 0

    for study_id in ARCHIVED_STUDY_IDS:
        src = out / "studies" / study_id
        if not src.is_dir():
            continue
        dest = archive / study_id
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(src), str(dest))
        moved += 1

    png_dir = png_export_dir(out)
    archive_png = archive / "png"
    archive_png.mkdir(parents=True, exist_ok=True)
    if png_dir.is_dir():
        for png in list(png_dir.glob("*.png")):
            if "rho_scan" in png.name or "sphere_legacy" in png.name:
                shutil.move(str(png), str(archive_png / png.name))
                moved += 1

    legacy_uniform = out / "rho_density_uniform.html"
    if legacy_uniform.exists():
        dest_html = archive / "rho_density_uniform.html"
        shutil.move(str(legacy_uniform), str(dest_html))
        legacy_png = png_dir / "rho_density_uniform.png"
        if legacy_png.exists():
            shutil.move(str(legacy_png), str(archive_png / legacy_png.name))
        moved += 1

    return moved


def png_export_dir(output_dir: str | Path = OUTPUT_DIR) -> Path:
    """차트 PNG export 일괄 저장 폴더."""
    return output_root(output_dir) / PNG_EXPORT_SUBDIR


def png_export_path(html_path: str | Path, output_dir: str | Path = OUTPUT_DIR) -> Path:
    """HTML 차트 경로 → output/png/ 내 PNG 경로."""
    html_path = Path(html_path)
    root = output_root(output_dir)
    try:
        rel = html_path.relative_to(root)
    except ValueError:
        rel = Path(html_path.name)
    flat = rel.with_suffix(".png").as_posix().replace("/", "__")
    return png_export_dir(root) / flat


def png_export_rel(html_path: str | Path, output_dir: str | Path = OUTPUT_DIR) -> str:
    """대시보드·fetch용 상대 URL."""
    return png_export_path(html_path, output_dir).relative_to(output_root(output_dir)).as_posix()


def migrate_png_exports(output_dir: str | Path = OUTPUT_DIR) -> int:
    """기존 분산 PNG → output/png/ 로 이동."""
    root = output_root(output_dir)
    dest_dir = png_export_dir(root)
    dest_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    for png in root.rglob("*.png"):
        if png.parent == dest_dir:
            continue
        if png.name.startswith("_"):
            continue
        try:
            rel = png.relative_to(root)
        except ValueError:
            continue
        flat = rel.with_suffix(".png").as_posix().replace("/", "__")
        dest = dest_dir / flat
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.resolve() == png.resolve():
            continue
        if dest.exists():
            png.unlink()
        else:
            shutil.move(str(png), str(dest))
        moved += 1
    return moved


def dashboard_path(output_dir: str | Path = OUTPUT_DIR) -> Path:
    """메인 대시보드 (GitHub Pages 루트 = index.html)."""
    return output_root(output_dir) / "index.html"


def comparison_path(output_dir: str | Path = OUTPUT_DIR) -> Path:
    """레거시 — 변인 통제 v2 비교 차트 (comparison_controlled.html 과 동일 내용)."""
    return output_root(output_dir) / "comparison.html"


def comparison_html_path(study_id: str, output_dir: str | Path = OUTPUT_DIR) -> Path:
    return output_root(output_dir) / f"comparison_{study_id}.html"


def history_path(output_dir: str | Path = OUTPUT_DIR) -> Path:
    return output_root(output_dir) / "history.json"


def preset_name_from_label(rho_label: str) -> str:
    """rho_label에서 프리셋 이름 추출 (alpha 접미사 제거)."""
    if "_alpha" in rho_label:
        return rho_label.split("_alpha", 1)[0]
    return rho_label


def variable_group_for_preset(preset_name: str, study_id: str | None = None) -> str | None:
    if preset_name == "uniform":
        return "uniform"
    spec = lookup_controlled_spec(preset_name)
    if spec:
        return spec["group"]
    if preset_name.startswith("sphere_"):
        return "legacy"
    if study_id == STUDY_SPHERE_LEGACY:
        return "legacy"
    return None


RHO_SCAN_ONLY_NAMES = {s["name"] for s in RHO_SCAN_SPECS}


def study_for_preset(preset_name: str) -> str | None:
    if preset_name in RHO_SCAN_ONLY_NAMES:
        return STUDY_RHO_SCAN
    if preset_name.startswith("ctrl_") or preset_name == "uniform":
        return STUDY_CONTROLLED
    if preset_name.startswith("sphere_"):
        return STUDY_SPHERE_LEGACY
    return None


def preset_index(study_id: str, preset_name: str) -> int | None:
    names = STUDY_PRESETS.get(study_id, [])
    try:
        return names.index(preset_name) + 1
    except ValueError:
        return None


def remove_study_density_preview(
    study_id: str,
    preset_name: str,
    output_dir: str | Path = OUTPUT_DIR,
) -> bool:
    """시뮬 완료 후 해당 설계용 밀도 미리보기 삭제."""
    idx = preset_index(study_id, preset_name)
    if idx is None:
        return False
    path = density_preview_path(study_id, idx, preset_name, output_dir)
    if path.exists():
        path.unlink()
        return True
    return False


def resolve_density_previews_dir(
    study_id: str,
    output_dir: str | Path = OUTPUT_DIR,
) -> Path | None:
    """새 경로 우선, 없으면 레거시 경로."""
    new_dir = density_previews_dir(study_id, output_dir)
    if new_dir.is_dir() and any(new_dir.glob("*.html")):
        return new_dir
    legacy_name = _LEGACY_STUDY_DIRS.get(study_id)
    if legacy_name:
        legacy = output_root(output_dir) / legacy_name / "density_previews"
        if legacy.is_dir() and any(legacy.glob("*.html")):
            return legacy
    return new_dir if new_dir.is_dir() else None


def reference_spec_for_group(study_id: str, variable_group: str) -> dict | None:
    """변인 그룹 헤더용 대표 스펙."""
    if variable_group == "uniform":
        return None
    groups = STUDY_VARIABLE_GROUPS.get(study_id, {})
    names = groups.get(variable_group, [])
    for name in names:
        spec = lookup_controlled_spec(name)
        if spec:
            return spec
    return None


def reorganize_output(output_dir: str | Path = OUTPUT_DIR, *, verbose: bool = True) -> dict:
    """
    기존 output/ 를 정리된 구조로 이전하고 불필요 파일 삭제.
    """
    from simulation.dashboard import collect_runs

    out = output_root(output_dir)
    stats = {"moved": 0, "deleted": 0, "skipped": 0}

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    for study_id, legacy_name in _LEGACY_STUDY_DIRS.items():
        legacy_previews = out / legacy_name / "density_previews"
        if not legacy_previews.is_dir():
            continue
        target = density_previews_dir(study_id, out)
        target.mkdir(parents=True, exist_ok=True)
        presets = STUDY_PRESETS[study_id]
        for i, name in enumerate(presets, 1):
            src = legacy_previews / f"{i:02d}_{name}.html"
            dst = target / f"{i:02d}_{name}.html"
            if src.exists() and not dst.exists():
                shutil.move(str(src), str(dst))
                stats["moved"] += 1
                log(f"  이동: {src.relative_to(out)} → {dst.relative_to(out)}")
        for stray in legacy_previews.glob("*.html"):
            stray.unlink()
            stats["deleted"] += 1
        for parent in [legacy_previews, out / legacy_name]:
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()

    for f in out.glob("rho_density_*.html"):
        f.unlink()
        stats["deleted"] += 1

    sim_runs = collect_runs(out)
    simulated: dict[str, set[str]] = {
        STUDY_SPHERE_LEGACY: set(),
        STUDY_CONTROLLED: set(),
        STUDY_CONTROLLED_V3: set(),
        STUDY_RHO_SCAN: set(),
    }

    for run in sim_runs:
        rho = run["rho_name"]
        extra_study = run.get("study_id")
        if extra_study in simulated:
            simulated[extra_study].add(rho)
        elif rho in RHO_SCAN_SIM_NAMES:
            simulated[STUDY_RHO_SCAN].add(rho)
        elif rho.startswith("ctrl_"):
            simulated[STUDY_CONTROLLED].add(rho)
        elif rho.startswith("sphere_"):
            simulated[STUDY_SPHERE_LEGACY].add(rho)
        elif rho == "uniform":
            has_ctrl = any(r["rho_name"].startswith("ctrl_") for r in sim_runs)
            if has_ctrl:
                simulated[STUDY_CONTROLLED].add(rho)

    for study_id, names in simulated.items():
        for name in names:
            if remove_study_density_preview(study_id, name, out):
                stats["deleted"] += 1

    for study_id, presets in STUDY_PRESETS.items():
        prev_dir = density_previews_dir(study_id, out)
        if not prev_dir.is_dir():
            continue
        valid = {f"{i:02d}_{n}.html" for i, n in enumerate(presets, 1)}
        for stray in prev_dir.glob("*.html"):
            if stray.name not in valid:
                stray.unlink()
                stats["deleted"] += 1

    return stats
