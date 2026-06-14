"""output/runs 결과를 한 페이지에서 탐색하는 대시보드 HTML."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from config import OUTPUT_DIR
from simulation.charts import (
    plot_probabilities,
    plot_runs_comparison,
    prob_y_axes_by_study,
    prob_series,
    study_from_results,
    unify_prob_y_axis,
)
from simulation.run_descriptions import (
    density_plot_title,
    enrich_items_with_conditions,
    export_png_filename_ko,
    preset_display_label_ko,
    probability_plot_title,
    variable_group_header_ko,
)
from simulation.output_layout import (
    ARCHIVED_STUDY_IDS,
    DASHBOARD_STUDY_IDS,
    STUDY_CONTROLLED,
    STUDY_LABELS,
    STUDY_PRESETS,
    STUDY_RHO_SCAN,
    STUDY_SPHERE_LEGACY,
    STUDY_VARIABLE_GROUPS,
    VARIABLE_GROUP_ORDER,
    comparison_html_path,
    comparison_path,
    density_preview_path,
    resolve_density_previews_dir,
    study_for_preset,
)


def _parse_run_dir(run_dir: Path, output_dir: Path) -> dict | None:
    prob_html = run_dir / "face_probabilities.html"
    if not prob_html.exists():
        return None

    density_html = run_dir / "rho_density.html"
    results_json = run_dir / "results.json"
    rel = lambda p: _rel(output_dir, p)

    rel_parts = run_dir.relative_to(output_dir).parts
    study_from_path: str | None = None
    vgroup_from_path: str | None = None
    rho_from_path: str | None = None

    if len(rel_parts) >= 5 and rel_parts[0] == "studies" and rel_parts[3] == "runs":
        study_from_path = rel_parts[1]
        vgroup_from_path = rel_parts[2]
        rho_from_path = rel_parts[4]
        run_id = "/".join(rel_parts[1:])
    else:
        run_id = run_dir.name
        rho_from_path = (
            run_dir.name.split("_", 2)[-1] if "_" in run_dir.name else run_dir.name
        )

    meta: dict = {
        "run_id": run_id,
        "rho_name": rho_from_path or run_dir.name,
        "n_trials": 0,
        "probabilities": {},
        "cancelled": False,
        "timestamp": "",
        "study_id": study_from_path,
        "variable_group": vgroup_from_path,
    }
    if results_json.exists():
        data = json.loads(results_json.read_text(encoding="utf-8"))
        meta["rho_name"] = data.get("rho_name", meta["rho_name"])
        meta["n_trials"] = data.get("n_trials", 0)
        meta["probabilities"] = data.get("probabilities", {})
        extra = data.get("extra") or {}
        meta["cancelled"] = bool(extra.get("cancelled"))
        meta["target_trials"] = extra.get("target_trials")
        meta["timestamp"] = data.get("timestamp", "")
        meta["study_id"] = extra.get("study_id") or meta["study_id"]
        meta["variable_group"] = extra.get("variable_group") or meta["variable_group"]

    probs = meta["probabilities"]
    top_face = "?"
    top_p = 0.0
    if probs:
        top_face = max(probs, key=probs.get)
        top_p = float(probs[top_face])

    return {
        **meta,
        "top_face": top_face,
        "top_p": top_p,
        "prob_url": rel(prob_html),
        "density_url": rel(density_html) if density_html.exists() else None,
    }


def _rel(output_dir: Path, path: Path) -> str:
    return path.relative_to(output_dir).as_posix()


def _preview_item(output_dir: Path, rel_path: Path, label: str) -> dict:
    stem = rel_path.stem
    return {
        "item_id": stem,
        "label": label,
        "display_label": preset_display_label_ko(label),
        "title": label,
        "density_url": _rel(output_dir, rel_path),
        "prob_url": None,
        "kind": "preview",
        "rho_name": label,
    }


def _sim_item(output_dir: Path, run: dict) -> dict:
    rho = run["rho_name"]
    return {
        "item_id": run["run_id"],
        "label": rho,
        "display_label": preset_display_label_ko(rho),
        "title": run["run_id"],
        "density_url": run.get("density_url"),
        "prob_url": run.get("prob_url"),
        "kind": "simulation",
        **run,
    }


def _infer_run_study(run: dict, all_runs: list[dict]) -> str | None:
    if run.get("study_id"):
        return run["study_id"]
    rho = run["rho_name"]
    inferred = study_for_preset(rho)
    if inferred:
        return inferred
    if rho.startswith("ctrl_"):
        return STUDY_CONTROLLED
    if rho.startswith("sphere_"):
        return STUDY_SPHERE_LEGACY
    if rho == "uniform":
        has_ctrl = any(r["rho_name"].startswith("ctrl_") for r in all_runs)
        if has_ctrl:
            return STUDY_CONTROLLED
        return STUDY_SPHERE_LEGACY
    return None


def _variable_group_order(study_id: str) -> list[str]:
    if study_id == STUDY_SPHERE_LEGACY:
        return ["legacy"]
    return [g for g in VARIABLE_GROUP_ORDER if g in STUDY_VARIABLE_GROUPS.get(study_id, {})]


def _build_variable_group_items(
    output_dir: Path,
    study_id: str,
    variable_group: str,
    preset_names: list[str],
    sim_runs: list[dict],
) -> list[dict]:
    runs_by_preset: dict[str, dict] = {}
    for run in sim_runs:
        if _infer_run_study(run, sim_runs) != study_id:
            continue
        if run.get("variable_group") and run["variable_group"] != variable_group:
            continue
        if run["rho_name"] not in preset_names:
            continue
        runs_by_preset[run["rho_name"]] = run

    items: list[dict] = []
    previews_dir = resolve_density_previews_dir(study_id, output_dir)
    for i, name in enumerate(preset_names, 1):
        if name in runs_by_preset:
            items.append(_sim_item(output_dir, runs_by_preset[name]))
        elif previews_dir:
            html = previews_dir / f"{i:02d}_{name}.html"
            if not html.exists():
                html = density_preview_path(study_id, i, name, output_dir)
            if html.exists():
                items.append(_preview_item(output_dir, html, name))
    return items


def collect_dashboard_studies(output_dir: str | Path = OUTPUT_DIR) -> list[dict]:
    """실험 → 변인 그룹 → 항목 구조로 수집."""
    output_dir = Path(output_dir)
    sim_runs = collect_runs(output_dir)
    used_run_ids: set[str] = set()
    studies: list[dict] = []

    study_order = list(DASHBOARD_STUDY_IDS)
    for study_id in study_order:
        vgroups = STUDY_VARIABLE_GROUPS.get(study_id, {})
        groups: list[dict] = []
        for vg_id in _variable_group_order(study_id):
            presets = vgroups.get(vg_id, [])
            if not presets:
                continue
            items = _build_variable_group_items(
                output_dir, study_id, vg_id, presets, sim_runs
            )
            if not items:
                continue
            for item in items:
                if item.get("kind") == "simulation":
                    used_run_ids.add(item["run_id"])
            groups.append(
                {
                    "id": vg_id,
                    "label": variable_group_header_ko(study_id, vg_id),
                    "items": items,
                }
            )
        if groups:
            studies.append(
                {
                    "id": study_id,
                    "label": STUDY_LABELS[study_id],
                    "groups": groups,
                }
            )

    other = [
        _sim_item(output_dir, run)
        for run in sim_runs
        if run["run_id"] not in used_run_ids
    ]
    if other:
        studies.append(
            {
                "id": "other",
                "label": "기타 시뮬",
                "groups": [{"id": "misc", "label": "분류 없음", "items": other}],
            }
        )

    return studies


def collect_dashboard_groups(output_dir: str | Path = OUTPUT_DIR) -> list[dict]:
    """하위 호환 — 실험 목록을 평탄 그룹으로."""
    studies = collect_dashboard_studies(output_dir)
    return [
        {
            "id": f"{s['id']}_study",
            "label": s["label"],
            "items": [it for g in s["groups"] for it in g["items"]],
        }
        for s in studies
    ]


def flatten_study_items(
    studies: list[dict],
    *,
    with_conditions: bool = True,
) -> list[dict]:
    """실험·변인 그룹 메타를 항목에 붙여 평탄화."""
    flat: list[dict] = []
    for study in studies:
        for group in study["groups"]:
            for item in group["items"]:
                flat.append(
                    {
                        **item,
                        "study_id": study["id"],
                        "study_label": study["label"],
                        "variable_group": group["id"],
                        "variable_group_label": group["label"],
                        "group_id": f"{study['id']}_{group['id']}",
                        "group_label": group["label"],
                    }
                )
    if with_conditions:
        return enrich_items_with_conditions(flat)
    return flat


def _slim_dashboard_item(item: dict) -> dict:
    """대시보드 JS용 경량 항목."""
    rho_name = item.get("rho_name") or item.get("label", "")
    n_trials = int(item.get("n_trials") or 0)
    return {
        "display_label": item.get("display_label") or item.get("label"),
        "density_url": item.get("density_url"),
        "prob_url": item.get("prob_url"),
        "cancelled": item.get("cancelled"),
        "group_id": item.get("group_id"),
        "group_label": item.get("group_label"),
        "study_id": item.get("study_id"),
        "study_label": item.get("study_label"),
        "png_prob": (
            export_png_filename_ko(rho_name, "prob", n_trials=n_trials)
            if item.get("prob_url")
            else None
        ),
        "png_density": (
            export_png_filename_ko(rho_name, "density")
            if item.get("density_url")
            else None
        ),
    }


def _slim_dashboard_studies(studies: list[dict]) -> list[dict]:
    """사이드바 렌더용 경량 실험 트리."""
    return [
        {
            "label": study["label"],
            "groups": [
                {
                    "label": group["label"],
                    "items": [
                        {
                            "display_label": it.get("display_label") or it.get("label"),
                            "cancelled": it.get("cancelled"),
                        }
                        for it in group["items"]
                    ],
                }
                for group in study["groups"]
            ],
        }
        for study in studies
    ]


def flatten_group_items(groups: list[dict]) -> list[dict]:
    """묶음 순서대로 항목 평탄화 + 한국어 조건 설명."""
    flat = []
    for g in groups:
        for item in g["items"]:
            flat.append({**item, "group_id": g["id"], "group_label": g["label"]})
    return enrich_items_with_conditions(flat)


def collect_runs(output_dir: str | Path = OUTPUT_DIR) -> list[dict]:
    """output/runs 및 studies/**/runs 아래 시뮬 폴더 수집."""
    output_dir = Path(output_dir)
    seen: set[str] = set()
    runs: list[dict] = []

    def add_run(run_dir: Path) -> None:
        key = str(run_dir.resolve())
        if key in seen:
            return
        entry = _parse_run_dir(run_dir, output_dir)
        if entry:
            seen.add(key)
            runs.append(entry)

    runs_root = output_dir / "runs"
    if runs_root.is_dir():
        for run_dir in sorted(runs_root.iterdir()):
            if run_dir.is_dir():
                add_run(run_dir)

    studies_root = output_dir / "studies"
    if studies_root.is_dir():
        for results_json in sorted(studies_root.rglob("results.json")):
            add_run(results_json.parent)

    runs.sort(key=lambda r: (r.get("study_id") or "", r.get("variable_group") or "", r["rho_name"]))
    return runs


def _artifact_up_to_date(artifact: Path, *sources: Path) -> bool:
    """산출물이 소스보다 최신이면 재생성 불필요."""
    if not artifact.exists():
        return False
    art_mtime = artifact.stat().st_mtime
    for src in sources:
        if src.exists() and src.stat().st_mtime > art_mtime:
            return False
    return True


def refresh_density_htmls(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    only_stale: bool = True,
) -> int:
    """studies/*/density_previews 및 runs/*/rho_density.html 재생성."""
    from density.analytic import SPHERE_STUDY_SIM_NAMES, get_preset_rho
    from density.grid import RhoGrid
    from density.visualize import plot_rho_grid

    output_dir = Path(output_dir)
    n = 0
    sim_runs = collect_runs(output_dir)

    for study_id, names in STUDY_PRESETS.items():
        if study_id in ARCHIVED_STUDY_IDS:
            continue
        previews = density_preview_path(study_id, 1, names[0], output_dir).parent
        previews.mkdir(parents=True, exist_ok=True)
        for i, name in enumerate(names, 1):
            has_sim = any(
                r["rho_name"] == name and _infer_run_study(r, sim_runs) == study_id
                for r in sim_runs
            )
            if has_sim:
                continue
            out_html = previews / f"{i:02d}_{name}.html"
            if only_stale and out_html.exists():
                continue
            grid = get_preset_rho(name)
            plot_rho_grid(
                grid,
                title=density_plot_title(name),
                save_path=out_html,
                show=False,
            )
            n += 1

    runs_root = output_dir / "runs"
    if runs_root.is_dir():
        for run_dir in sorted(runs_root.iterdir()):
            if not run_dir.is_dir():
                continue
            npy = run_dir / "rho_grid.npy"
            out_html = run_dir / "rho_density.html"
            if not npy.exists():
                continue
            if only_stale and _artifact_up_to_date(out_html, npy):
                continue
            grid = RhoGrid.load(npy)
            rho_name = run_dir.name.split("_", 2)[-1] if "_" in run_dir.name else run_dir.name
            plot_rho_grid(
                grid,
                title=density_plot_title(rho_name),
                save_path=out_html,
                show=False,
            )
            n += 1

    studies_root = output_dir / "studies"
    if studies_root.is_dir():
        for run_dir in sorted(studies_root.rglob("rho_grid.npy")):
            run_dir = run_dir.parent
            out_html = run_dir / "rho_density.html"
            npy = run_dir / "rho_grid.npy"
            if only_stale and _artifact_up_to_date(out_html, npy):
                continue
            grid = RhoGrid.load(npy)
            rho_name = run_dir.name
            plot_rho_grid(
                grid,
                title=density_plot_title(rho_name),
                save_path=out_html,
                show=False,
            )
            n += 1

    return n


def _build_study_comparison_charts(
    output_dir: Path,
    flat: list[dict],
    runs: list[dict],
) -> dict[str, str]:
    """실험 묶음별 비교 차트 HTML 생성 → {study_id: 상대 URL}."""
    study_axes = prob_y_axes_by_study(output_dir)
    compare_urls: dict[str, str] = {}

    for study_id in DASHBOARD_STUDY_IDS:
        study_run_ids = {
            it["run_id"]
            for it in flat
            if it.get("kind") == "simulation"
            and it.get("study_id") == study_id
            and it.get("run_id")
        }
        if len(study_run_ids) < 2:
            continue
        comparison_runs = [r for r in runs if r["run_id"] in study_run_ids]
        if len(comparison_runs) < 2:
            continue

        preset_order = {
            name: i for i, name in enumerate(STUDY_PRESETS.get(study_id, []))
        }
        comparison_runs.sort(
            key=lambda r: preset_order.get(r["rho_name"], 999)
        )

        comp_path = comparison_html_path(study_id, output_dir)
        label = STUDY_LABELS.get(study_id, study_id)
        comp_y = study_axes.get(study_id)
        plot_runs_comparison(
            comparison_runs,
            comp_path,
            title=(
                "바닥의 눈 확률 분포 비교",
                f"{label} — {len(comparison_runs)}개 시뮬레이션",
            ),
            y_range=comp_y[0] if comp_y else None,
            y_dtick=comp_y[1] if comp_y else None,
        )
        compare_urls[study_id] = comp_path.relative_to(output_dir).as_posix()

    if STUDY_CONTROLLED in compare_urls:
        legacy = comparison_path(output_dir)
        shutil.copy2(output_dir / compare_urls[STUDY_CONTROLLED], legacy)

    return compare_urls


def build_dashboard(output_dir: str | Path = OUTPUT_DIR) -> Path:
    """통합 대시보드 HTML 생성. 경로: output/index.html"""
    from simulation.output_layout import dashboard_path as index_path

    output_dir = Path(output_dir)
    studies = collect_dashboard_studies(output_dir)
    flat = flatten_study_items(studies, with_conditions=False)
    runs = collect_runs(output_dir)
    dashboard_path = index_path(output_dir)

    if not flat:
        dashboard_path.write_text(
            """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
            <title>시뮬레이션 대시보드</title></head>
            <body><h1>시뮬레이션 대시보드</h1>
            <p>표시할 밀도/시뮬 결과가 없습니다.</p></body></html>""",
            encoding="utf-8",
        )
        return dashboard_path

    studies_json = json.dumps(_slim_dashboard_studies(studies), ensure_ascii=False)
    flat_json = json.dumps([_slim_dashboard_item(it) for it in flat], ensure_ascii=False)
    chart_cache_v = str(int(time.time()))
    n_density = sum(1 for it in flat if it.get("density_url"))
    n_sim = sum(1 for it in flat if it.get("prob_url"))

    compare_urls = _build_study_comparison_charts(output_dir, flat, runs)
    compare_urls_json = json.dumps(compare_urls, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>시뮬레이션 결과 대시보드</title>
  <style>
    :root {{
      --bg: #f1f5f9;
      --surface: #ffffff;
      --sidebar: #0f172a;
      --sidebar-muted: #94a3b8;
      --text: #0f172a;
      --text-muted: #64748b;
      --accent: #2563eb;
      --accent-soft: #dbeafe;
      --border: #e2e8f0;
      --radius: 10px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ height: 100%; overflow: hidden; }}
    body {{
      font-family: "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
    }}
    header {{
      flex-shrink: 0;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 10px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      z-index: 10;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }}
    .brand {{ display: flex; flex-direction: column; gap: 2px; }}
    header h1 {{ font-size: 1.05rem; font-weight: 700; letter-spacing: -0.02em; }}
    #run-count {{ font-size: 0.75rem; color: var(--text-muted); }}
    .toolbar {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; flex: 1; justify-content: flex-end; }}
    .view-tabs {{
      display: flex;
      gap: 4px;
      padding: 4px;
      background: var(--bg);
      border-radius: var(--radius);
      border: 1px solid var(--border);
    }}
    .view-tabs button, .toolbar > button {{
      font: inherit;
      font-size: 0.875rem;
      padding: 8px 14px;
      border: 1px solid transparent;
      border-radius: 8px;
      background: transparent;
      cursor: pointer;
      color: var(--text);
      transition: background 0.15s, color 0.15s, border-color 0.15s;
    }}
    .view-tabs button {{
      font-weight: 500;
    }}
    .view-tabs button.active {{
      background: var(--accent);
      color: #fff;
      box-shadow: 0 1px 3px rgba(37, 99, 235, 0.35);
    }}
    .view-tabs button:disabled {{ opacity: 0.35; cursor: not-allowed; }}
    .view-tabs button:hover:not(:disabled):not(.active) {{ background: var(--surface); }}
    .panel-toggle {{
      border: 1px solid var(--border);
      background: var(--surface);
    }}
    .panel-toggle.on {{ background: var(--accent-soft); border-color: #93c5fd; color: var(--accent); }}
    .panel-toggle:hover {{ background: #f8fafc; }}
    .export-btn {{
      border: 1px solid #93c5fd;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 700;
      white-space: nowrap;
      padding: 8px 14px;
      border-radius: 8px;
    }}
    .export-btn:hover:not(:disabled) {{
      background: var(--accent-soft);
      border-color: #93c5fd;
      color: var(--accent);
    }}
    .export-btn:disabled {{ opacity: 0.35; cursor: not-allowed; }}
    .nav-controls {{
      display: flex;
      align-items: stretch;
      gap: 8px;
      flex: 1;
      min-width: 0;
      max-width: 420px;
    }}
    .nav-controls.hidden {{ display: none; }}
    .nav-controls button {{
      flex-shrink: 0;
      width: 52px;
      min-height: 52px;
      border: 1px solid var(--border);
      background: var(--surface);
      border-radius: 10px;
      font-size: 1.5rem;
      line-height: 1;
      color: var(--accent);
      font-weight: 700;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
    }}
    .nav-controls button:hover:not(:disabled) {{ background: var(--accent-soft); border-color: #93c5fd; }}
    .nav-controls button:active:not(:disabled) {{ transform: scale(0.97); }}
    .nav-controls button:disabled {{
      opacity: 0.35;
      color: var(--text-muted);
      background: var(--bg);
      border-color: var(--border);
      box-shadow: none;
    }}
    .nav-current {{
      flex: 1;
      min-width: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 12px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--bg);
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: var(--text);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .layout {{ display: flex; flex: 1; min-height: 0; overflow: hidden; }}
    aside {{
      width: 280px;
      background: var(--sidebar);
      color: #f8fafc;
      overflow-y: auto;
      flex-shrink: 0;
      transition: width 0.2s ease;
    }}
    body.sidebar-hidden aside {{ width: 0; overflow: hidden; }}
    .run-list {{ list-style: none; }}
    .study-header {{
      padding: 14px 16px 4px;
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: #64748b;
      background: #0b1220;
    }}
    .group-header {{
      padding: 12px 16px 8px 16px;
      font-size: 0.78rem;
      font-weight: 600;
      line-height: 1.45;
      color: #e2e8f0;
      background: #1e293b;
      border-top: 1px solid #334155;
    }}
    .run-item {{
      padding: 11px 16px 11px 28px;
      border-bottom: 1px solid #1e293b;
      border-left: 3px solid transparent;
      cursor: pointer;
      transition: background 0.12s, border-color 0.12s;
    }}
    .run-item:hover {{ background: #1e293b; }}
    .run-item.active {{
      background: var(--accent);
      border-left-color: #bfdbfe;
    }}
    .run-item .name {{ font-weight: 600; font-size: 0.95rem; line-height: 1.35; }}
    .badge {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.65rem;
      background: #fef3c7;
      color: #92400e;
    }}
    main {{
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
      min-height: 0;
      background: var(--surface);
      overflow: hidden;
    }}
    .viewer-wrap {{
      flex: 1;
      min-height: 0;
      position: relative;
      background: #fafbfc;
    }}
    .viewer-wrap.density-view {{
      display: flex;
      align-items: stretch;
      justify-content: center;
      padding: 6px 8px 10px;
    }}
    .viewer-wrap.density-view iframe {{
      width: 100%;
      max-width: 100%;
      height: 100%;
      border-radius: 8px;
      box-shadow: 0 2px 14px rgba(15, 23, 42, 0.07);
      background: #fff;
    }}
    iframe {{
      width: 100%;
      height: 100%;
      border: none;
      display: block;
      min-height: 280px;
      background: #fafbfc;
    }}
    .viewer-loading {{
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(248, 250, 252, 0.85);
      color: var(--text-muted);
      font-size: 0.9rem;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s;
    }}
    .viewer-loading.visible {{ opacity: 1; }}
    @media (max-width: 768px) {{
      html, body {{
        height: 100%;
        height: 100dvh;
        overflow: hidden;
        width: 100%;
        overscroll-behavior: none;
      }}
      body {{
        padding: 0;
      }}
      .brand {{ display: none; }}
      header {{
        position: relative;
        flex-shrink: 0;
        z-index: 120;
        background: var(--surface);
        padding: 6px 10px;
        padding-top: max(6px, env(safe-area-inset-top));
        gap: 4px;
        flex-wrap: nowrap;
      }}
      .toolbar {{
        width: 100%;
        display: grid;
        grid-template-columns: 1fr auto auto;
        grid-template-rows: auto auto;
        gap: 4px 6px;
        align-items: stretch;
      }}
      .nav-controls {{
        grid-column: 1 / -1;
        order: unset;
        max-width: none;
        width: 100%;
      }}
      .nav-controls button {{
        width: 52px;
        min-height: 48px;
        font-size: 1.6rem;
      }}
      .nav-current {{
        font-size: 1rem;
        min-height: 48px;
      }}
      .view-tabs {{
        grid-column: 1 / 2;
        order: unset;
        width: auto;
      }}
      .view-tabs button {{
        flex: 1;
        padding: 7px 4px;
        font-size: 0.78rem;
      }}
      #btn-export-group {{
        grid-column: 2 / 3;
        order: unset;
        width: auto;
        min-height: 38px;
        padding: 6px 10px;
        font-size: 0.72rem;
      }}
      .panel-toggle {{
        grid-column: 3 / 4;
        order: unset;
        width: auto;
        min-width: 48px;
        min-height: 38px;
        font-size: 0.82rem;
        padding: 6px 10px;
      }}
      .layout {{
        flex: 1;
        flex-direction: column;
        min-height: 0;
        overflow: hidden;
        overscroll-behavior: none;
      }}
      main {{ flex: 1; min-height: 0; display: flex; flex-direction: column; }}
      aside {{
        width: 100%;
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        max-height: min(55dvh, 420px);
        padding-bottom: env(safe-area-inset-bottom);
        z-index: 50;
        box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.25);
        border-radius: 14px 14px 0 0;
      }}
      body.sidebar-hidden aside {{ display: none; }}
      .viewer-wrap {{
        flex: 1 1 0;
        width: 100%;
        min-height: 0;
        overflow: hidden;
        -webkit-overflow-scrolling: touch;
      }}
      body.compare-view .viewer-wrap {{
        overflow: hidden;
      }}
      body.compare-view iframe {{
        display: block;
        height: 100%;
      }}
      .viewer-wrap.density-view {{ padding: 4px 0 4px 4px; }}
      iframe {{ min-height: 0; height: 100%; touch-action: manipulation; }}
    }}
  </style>
</head>
<body class="sidebar-hidden">
  <header>
    <div class="brand">
      <h1>시뮬레이션 대시보드</h1>
      <span id="run-count">질량 {n_density} · 시뮬 {n_sim}</span>
    </div>
    <div class="toolbar">
      <div class="nav-controls" id="nav-controls">
        <button type="button" id="btn-prev" title="이전" aria-label="이전">‹</button>
        <span class="nav-current" id="nav-current" aria-live="polite"></span>
        <button type="button" id="btn-next" title="다음" aria-label="다음">›</button>
      </div>
      <div class="view-tabs">
        <button type="button" data-view="prob">확률분포</button>
        <button type="button" class="active" data-view="density">질량분포</button>
        <button type="button" data-view="compare">분포 비교</button>
      </div>
      <button type="button" class="export-btn" id="btn-export-group" title="현재 실험 묶음의 질량·확률 PNG를 ZIP으로 저장">묶음 PNG</button>
      <button type="button" class="panel-toggle" id="toggle-sidebar" title="목록">☰ 목록</button>
    </div>
  </header>
  <div class="layout">
    <aside id="sidebar"><ul class="run-list" id="run-list"></ul></aside>
    <main>
      <div class="viewer-wrap">
        <div class="viewer-loading" id="viewer-loading" aria-hidden="true">불러오는 중…</div>
        <iframe id="viewer" title="뷰어"></iframe>
      </div>
    </main>
  </div>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js" crossorigin="anonymous"></script>
  <script>
    const STUDIES = {studies_json};
    const ITEMS = {flat_json};
    const CHART_CACHE_V = "{chart_cache_v}";
    let index = 0;
    let view = "density";
    let currentSrc = "";
    const COMPARE_URLS = {compare_urls_json};

    function chartUrl(url) {{
      if (!url) return "";
      const sep = url.includes("?") ? "&" : "?";
      return url + sep + "v=" + CHART_CACHE_V;
    }}

    const elList = document.getElementById("run-list");
    const elViewer = document.getElementById("viewer");
    const elLoading = document.getElementById("viewer-loading");
    const elNavCurrent = document.getElementById("nav-current");
    const btnSidebar = document.getElementById("toggle-sidebar");
    const btnPrev = document.getElementById("btn-prev");
    const btnNext = document.getElementById("btn-next");
    const btnExportGroup = document.getElementById("btn-export-group");
    const viewerWrap = document.querySelector(".viewer-wrap");
    const navControls = document.getElementById("nav-controls");

    function safeExportName(s) {{
      return String(s).replace(/[\\\\/:*?"<>|]/g, "_").trim().slice(0, 80) || "simulation";
    }}

    async function capturePlotPng(url) {{
      const iframe = document.createElement("iframe");
      iframe.style.cssText =
        "position:fixed;opacity:0;pointer-events:none;left:-12000px;top:0;"
        + "width:1400px;height:1000px;border:0";
      document.body.appendChild(iframe);
      try {{
        await new Promise((resolve, reject) => {{
          iframe.onload = () => resolve();
          iframe.onerror = () => reject(new Error(url));
          iframe.src = url;
        }});
        await new Promise(r => setTimeout(r, 1400));
        const win = iframe.contentWindow;
        const plot = win.document.querySelector(".js-plotly-plot");
        if (!plot || !win.Plotly) throw new Error("plotly");
        const dataUrl = await win.Plotly.toImage(plot, {{
          format: "png",
          width: 1400,
          height: 1000,
          scale: 2,
        }});
        const bin = atob(dataUrl.split(",")[1]);
        const arr = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        return new Blob([arr], {{ type: "image/png" }});
      }} finally {{
        iframe.remove();
      }}
    }}

    async function fetchOrCapturePng(htmlUrl) {{
      const busted = chartUrl(pngUrlFromHtml(htmlUrl));
      try {{
        const resp = await fetch(busted);
        if (resp.ok) return await resp.blob();
      }} catch (e) {{ /* prebuilt png 없음 */ }}
      return capturePlotPng(chartUrl(htmlUrl));
    }}

    function pngUrlFromHtml(htmlUrl) {{
      const path = htmlUrl.replace(/\\?.*$/, "").replace(/\\.html$/i, "");
      return "png/" + path.replace(/\\//g, "__") + ".png";
    }}

    function exportTimestamp() {{
      const d = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      return (
        d.getFullYear()
        + pad(d.getMonth() + 1)
        + pad(d.getDate()) + "_"
        + pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds())
      );
    }}

    function studyFolderBase(label) {{
      if (!label) return "simulation";
      return safeExportName(label);
    }}

    function compareUrlForStudy(studyId) {{
      if (!studyId) return null;
      return COMPARE_URLS[studyId] || null;
    }}

    function compareUrlForCurrentStudy() {{
      const it = ITEMS[index];
      return it && it.study_id ? compareUrlForStudy(it.study_id) : null;
    }}

    function currentStudyHasCompare() {{
      return !!compareUrlForCurrentStudy();
    }}

    function studyExportFolderName(label) {{
      return studyFolderBase(label) + "_" + exportTimestamp();
    }}

    function collectStudyPngEntries(studyId) {{
      const entries = [];
      for (const it of ITEMS) {{
        if (it.study_id !== studyId) continue;
        if (it.density_url && it.png_density) {{
          entries.push({{
            url: it.density_url,
            pngName: safeExportName(it.png_density) + ".png",
          }});
        }}
        if (it.prob_url && it.png_prob) {{
          entries.push({{
            url: it.prob_url,
            pngName: safeExportName(it.png_prob) + ".png",
          }});
        }}
      }}
      return entries;
    }}

    async function exportGroupPngBundle() {{
      if (view === "compare") return;
      const it = ITEMS[index];
      const studyId = it.study_id;
      if (!studyId) {{
        alert("실험 묶음 정보가 없습니다.");
        return;
      }}
      const entries = collectStudyPngEntries(studyId);
      if (!entries.length) {{
        alert("저장할 PNG가 없습니다.");
        return;
      }}
      if (typeof JSZip === "undefined") {{
        alert("PNG 저장 모듈을 불러오지 못했습니다. 네트워크 연결을 확인해 주세요.");
        return;
      }}
      const folderName = studyExportFolderName(it.study_label);
      const folderPrefix = folderName + "/";
      btnExportGroup.disabled = true;
      const prevText = btnExportGroup.textContent;
      try {{
        const zip = new JSZip();
        let saved = 0;
        for (let i = 0; i < entries.length; i++) {{
          btnExportGroup.textContent = (i + 1) + "/" + entries.length + "…";
          try {{
            const pngBlob = await fetchOrCapturePng(entries[i].url);
            zip.file(folderPrefix + entries[i].pngName, pngBlob);
            saved += 1;
          }} catch (pngErr) {{
            console.warn("PNG 생성 실패:", entries[i].url, pngErr);
          }}
        }}
        if (!saved) {{
          alert("PNG를 만들지 못했습니다. 차트를 다시 빌드했는지 확인해 주세요.");
          return;
        }}
        const blob = await zip.generateAsync({{ type: "blob" }});
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = folderName + ".zip";
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 2000);
      }} catch (err) {{
        console.error(err);
        alert("PNG 저장에 실패했습니다. 같은 주소에서 대시보드를 열었는지 확인해 주세요.");
      }} finally {{
        btnExportGroup.textContent = prevText;
        const sid = ITEMS[index] && ITEMS[index].study_id;
        btnExportGroup.disabled = view === "compare" || !sid
          || collectStudyPngEntries(sid).length === 0;
      }}
    }}

    btnExportGroup.addEventListener("click", () => exportGroupPngBundle());

    function escapeHtml(s) {{
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }}

    let resizeTimer = null;

    function syncCompareIframeHeight() {{
      if (view !== "compare" || !window.matchMedia("(max-width: 768px)").matches) return;
      const wrap = document.querySelector(".viewer-wrap");
      if (!wrap) return;
      elViewer.style.height = Math.max(200, wrap.clientHeight) + "px";
    }}

    function resizeViewer() {{
      const header = document.querySelector("header");
      const wrap = document.querySelector(".viewer-wrap");
      const iframe = document.getElementById("viewer");
      if (!header || !wrap || !iframe) return;
      if (window.matchMedia("(max-width: 768px)").matches) {{
        wrap.style.height = "";
        wrap.style.flex = "1 1 auto";
        const wrapH = Math.max(200, wrap.clientHeight || 0);
        if (view === "compare") {{
          wrap.style.overflowY = "hidden";
          iframe.style.height = wrapH + "px";
          iframe.style.minHeight = "";
          iframe.scrolling = "no";
        }} else {{
          wrap.style.overflowY = "hidden";
          iframe.style.height = "100%";
          iframe.style.minHeight = "";
          iframe.scrolling = "no";
        }}
        if (view === "compare") {{
          syncCompareIframeHeight();
          setTimeout(syncCompareIframeHeight, 150);
          setTimeout(syncCompareIframeHeight, 500);
        }}
      }} else {{
        wrap.style.height = "";
        wrap.style.flex = "";
        iframe.style.height = "100%";
      }}
    }}
    function scheduleResize() {{
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resizeViewer, 80);
    }}

    function setPanel(btn, cls, hidden) {{
      document.body.classList.toggle(cls, hidden);
      btn.classList.toggle("on", !hidden);
    }}
    btnSidebar.addEventListener("click", () => {{
      setPanel(btnSidebar, "sidebar-hidden", !document.body.classList.contains("sidebar-hidden"));
      scheduleResize();
    }});

    function buildUI() {{
      elList.innerHTML = "";
      let flatIdx = 0;
      const multiStudy = STUDIES.length > 1;
      STUDIES.forEach(study => {{
        const showStudy = multiStudy || study.groups.length > 1;
        if (showStudy) {{
          const sh = document.createElement("li");
          sh.className = "study-header";
          sh.textContent = study.label;
          elList.appendChild(sh);
        }}
        study.groups.forEach(group => {{
          const gh = document.createElement("li");
          gh.className = "group-header";
          gh.textContent = group.label;
          elList.appendChild(gh);
          group.items.forEach(item => {{
            const i = flatIdx;
            const li = document.createElement("li");
            li.className = "run-item" + (i === index ? " active" : "");
            li.dataset.flatIndex = String(i);
            const cancelled = item.cancelled ? ' <span class="badge">중단</span>' : "";
            const disp = item.display_label || "";
            li.innerHTML = '<div class="name">' + escapeHtml(disp) + cancelled + '</div>';
            li.addEventListener("click", () => {{ selectItem(i); setPanel(btnSidebar, "sidebar-hidden", true); }});
            elList.appendChild(li);
            flatIdx++;
          }});
        }});
      }});
    }}

    function currentUrl() {{
      if (view === "compare") return compareUrlForCurrentStudy() || "";
      const it = ITEMS[index];
      if (view === "density") return it.density_url || "";
      return it.prob_url || "";
    }}

    function setViewerUrl(url) {{
      if (!url) {{
        currentSrc = "";
        elViewer.removeAttribute("src");
        elLoading.classList.remove("visible");
        return;
      }}
      const busted = chartUrl(url);
      if (busted === currentSrc) return;
      currentSrc = busted;
      elLoading.classList.add("visible");
      elViewer.src = busted;
    }}

    function itemHasViewUrl(i) {{
      if (i < 0 || i >= ITEMS.length) return false;
      const it = ITEMS[i];
      return view === "density" ? !!it.density_url : !!it.prob_url;
    }}

    function findNavIndex(delta) {{
      let i = index + delta;
      while (i >= 0 && i < ITEMS.length) {{
        if (itemHasViewUrl(i)) return i;
        i += delta;
      }}
      return null;
    }}

    function updateNavButtons() {{
      if (view === "compare") {{
        btnPrev.disabled = true;
        btnNext.disabled = true;
        return;
      }}
      btnPrev.disabled = findNavIndex(-1) === null;
      btnNext.disabled = findNavIndex(1) === null;
    }}

    function updateView() {{
      const isCompare = view === "compare";
      document.body.classList.toggle("compare-view", isCompare);
      navControls.classList.remove("hidden");
      const it = ITEMS[index];
      if (viewerWrap) {{
        viewerWrap.classList.toggle("density-view", view === "density" && !isCompare);
        if (isCompare) viewerWrap.scrollTop = 0;
      }}
      if (btnExportGroup) {{
        const sid = it.study_id;
        btnExportGroup.disabled = isCompare || !sid
          || collectStudyPngEntries(sid).length === 0;
        if (it.study_label) {{
          btnExportGroup.title = it.study_label + " 전체 질량·확률 PNG를 ZIP으로 저장";
        }}
      }}
      setViewerUrl(currentUrl());
      scheduleResize();
      document.querySelectorAll(".run-item").forEach(el => {{
        el.classList.toggle("active", parseInt(el.dataset.flatIndex, 10) === index);
      }});

      if (isCompare) {{
        const cmpLabel = it.study_label ? ("분포 비교 — " + it.study_label) : "분포 비교";
        elNavCurrent.textContent = cmpLabel;
        updateNavButtons();
        document.querySelectorAll(".view-tabs button").forEach(btn => {{
          btn.classList.toggle("active", btn.dataset.view === view);
          btn.disabled = btn.dataset.view === "compare" && !currentStudyHasCompare();
        }});
        return;
      }}

      elNavCurrent.textContent = it.display_label || "";
      updateNavButtons();

      document.querySelectorAll(".view-tabs button").forEach(btn => {{
        const v = btn.dataset.view;
        btn.classList.toggle("active", v === view);
        if (v === "prob") btn.disabled = !it.prob_url;
        if (v === "density") btn.disabled = !it.density_url;
        if (v === "compare") btn.disabled = !currentStudyHasCompare();
      }});
    }}

    function selectItem(i) {{
      index = Math.max(0, Math.min(ITEMS.length - 1, i));
      if (view === "prob" && !ITEMS[index].prob_url) view = "density";
      if (view === "compare" && !compareUrlForCurrentStudy()) view = "density";
      updateView();
    }}

    function step(delta) {{
      if (view === "compare") return;
      const target = findNavIndex(delta);
      if (target === null) return;
      selectItem(target);
    }}

    btnPrev.addEventListener("click", () => step(-1));
    btnNext.addEventListener("click", () => step(1));
    document.querySelectorAll(".view-tabs button").forEach(btn => {{
      btn.addEventListener("click", () => {{
        if (btn.disabled) return;
        view = btn.dataset.view;
        if (view === "prob" && !ITEMS[index].prob_url) {{
          const j = ITEMS.findIndex(x => x.prob_url);
          if (j >= 0) index = j;
        }}
        updateView();
      }});
    }});

    buildUI();
    resizeViewer();
    updateView();
    window.addEventListener("resize", scheduleResize);
    window.addEventListener("orientationchange", () => setTimeout(resizeViewer, 300));
    if (window.visualViewport) {{
      window.visualViewport.addEventListener("resize", scheduleResize);
    }}
    elViewer.addEventListener("load", () => {{
      elLoading.classList.remove("visible");
      scheduleResize();
      try {{
        const doc = elViewer.contentDocument || elViewer.contentWindow.document;
        const plot = doc && doc.querySelector(".js-plotly-plot");
        if (plot && elViewer.contentWindow.Plotly) {{
          elViewer.contentWindow.Plotly.Plots.resize(plot);
        }}
        if (view === "compare" && doc) {{
          syncCompareIframeHeight();
          setTimeout(syncCompareIframeHeight, 150);
          setTimeout(syncCompareIframeHeight, 500);
        }}
      }} catch (e) {{ /* plotly 3d */ }}
    }});
  </script>
</body>
</html>"""

    dashboard_path.write_text(html, encoding="utf-8")
    return dashboard_path


def refresh_probability_charts(
    output_dir: str | Path = OUTPUT_DIR,
    *,
    only_stale: bool = True,
    run_ids: set[str] | None = None,
) -> int:
    """기존 runs의 face_probabilities.html을 막대 라벨 포함 형식으로 다시 생성."""
    output_dir = Path(output_dir)
    group_axes = prob_y_axes_by_study(output_dir)
    n = 0
    for run in collect_runs(output_dir):
        if run_ids is not None and run["run_id"] not in run_ids:
            continue
        results_path = output_dir / "runs" / run["run_id"] / "results.json"
        if not results_path.exists():
            continue
        target = output_dir / Path(run["prob_url"])
        if only_stale and _artifact_up_to_date(target, results_path):
            continue
        data = json.loads(results_path.read_text(encoding="utf-8"))
        probs = {int(k): float(v) for k, v in data["probabilities"].items()}
        n_trials = data["n_trials"]
        extra = data.get("extra") or {}
        cancelled = extra.get("cancelled")
        target = extra.get("target_trials", n_trials)
        sid = study_from_results(data)
        if sid in group_axes:
            y_range, y_dtick = group_axes[sid]
        else:
            y_range, y_dtick = unify_prob_y_axis([prob_series(probs, n_trials)])
        plot_probabilities(
            probs,
            n_trials,
            title=probability_plot_title(
                data["rho_name"],
                n_trials,
                cancelled=cancelled,
                target_trials=target,
            ),
            save_path=target,
            y_range=y_range,
            y_dtick=y_dtick,
        )
        n += 1
    return n
