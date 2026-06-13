"""시뮬레이션·밀도 프리셋별 한국어 조건 설명."""

from __future__ import annotations

from typing import Any

from config import (
    ANG_VEL_THRESHOLD,
    DIE_HALF_SIZE,
    DROP_HEIGHT,
    FRICTION,
    GRID_N,
    MAX_ANGULAR_VEL,
    MAX_SIM_STEPS,
    PHYSICS_DT,
    RESTITUTION,
    SETTLE_TIME,
    VEL_THRESHOLD,
)
from density.analytic import (
    ALL_CONTROLLED_SPECS,
    CONTROLLED_STUDY_SPECS,
    SPHERE_STUDY_SPECS,
    lookup_controlled_spec,
)

# 구형 bump 밀도: 구 내부 ρ=factor, 바깥 ρ=1
_BUMP_TEMPLATE = (
    "구형 고밀도 영역: {x_desc}, {r_desc}, "
    "구 안 {f_desc}, 구 밖 ρ=1 (기준)"
)


def _fmt_x0(x0: float) -> str:
    return f"편심x좌표={x0:g}"


def _fmt_radius(radius: float) -> str:
    return f"반지름={radius:g}"


def _fmt_factor(factor: float) -> str:
    return f"ρ={factor:g}"


def _fmt_density(factor: float) -> str:
    return f"밀도={factor:g}"


def _fmt_x0_prob(x0: float) -> str:
    """확률 차트 제목용."""
    return f"편심 x좌표={x0:g}"


def _parse_name_x(encoded: str) -> float:
    """프리셋 이름 접미사 x28 → 0.28"""
    return int(encoded) / 100.0


def _parse_name_r(encoded: str) -> float:
    """r16 → 0.16"""
    return int(encoded) / 100.0


def _parse_name_f(encoded: str) -> float:
    """f30 → 3.0"""
    return int(encoded) / 10.0


def global_physics_lines() -> list[str]:
    """모든 시행에 공통인 PyBullet·낙하 조건."""
    return [
        f"주사위 크기: 한 변 {2 * DIE_HALF_SIZE:.1f} m (중심 원점, 범위 [−0.5, 0.5]³)",
        f"밀도 격자: {GRID_N}×{GRID_N}×{GRID_N} = {GRID_N**3}칸 (질량·관성 계산용)",
        "강체 모델: 겉모양은 대칭 정육면체, 질량 분포만 비대칭 (COM·관성텐서 반영)",
        f"낙하 높이: 주사위 중심 z = {DROP_HEIGHT} m 에서 시작",
        f"초기 선속도: (0, 0, 0) — 던지지 않고 떨어뜨림",
        f"초기 각속도: 각 축 ±{MAX_ANGULAR_VEL} rad/s 균일 랜덤",
        f"바닥 마찰 μ = {FRICTION}, 반발계수 e = {RESTITUTION}",
        f"정지 판정: |v| < {VEL_THRESHOLD} m/s, |ω| < {ANG_VEL_THRESHOLD} rad/s "
        f"가 {SETTLE_TIME}초 연속",
        f"시뮬 스텝: Δt = 1/240 s, 최대 {MAX_SIM_STEPS}스텝 (약 {MAX_SIM_STEPS * PHYSICS_DT:.1f}초)",
        "결과 측정: 정지 후 바닥(−z)에 닿은 면 번호 (1~6)",
    ]


def _uniform_lines() -> list[str]:
    return [
        "밀도: 모든 위치 ρ = 1 (균일, 공정 주사위 기준선)",
        "질량중심 ≈ 원점, 관성 ≈ 대칭",
    ]


def _sphere_spec_lines(spec: dict) -> list[str]:
    x0, radius, factor = spec["x0"], spec["radius"], spec["factor"]
    return [
        _BUMP_TEMPLATE.format(
            x_desc=f"중심 ({x0:g}, 0, 0)",
            r_desc=_fmt_radius(radius),
            f_desc=f"ρ={factor:g}",
        ),
        f"+x 방향으로 질량이 치우친 비대칭 주사위 ({_fmt_x0(x0)})",
    ]


def _controlled_spec_lines(spec: dict) -> list[str]:
    lines = _sphere_spec_lines(spec)
    g = spec["group"]
    x0, r, f = spec["x0"], spec["radius"], spec["factor"]
    rho = _fmt_factor(f)
    if g == "factor":
        lines.append(
            f"변인 통제 A(밀도): {_fmt_x0(x0)}, {_fmt_radius(r)} 고정, "
            f"구 안 {rho} 만 변경 (구 밖 ρ=1)"
        )
    elif g == "radius":
        lines.append(
            f"변인 통제 B(반지름): {_fmt_x0(x0)}, 구 안 {rho} 고정, "
            f"{_fmt_radius(r)} 만 변경"
        )
    elif g == "center":
        lines.append(
            f"변인 통제 C(중심): {_fmt_radius(r)}, 구 안 {rho} 고정, "
            f"{_fmt_x0(x0)} 만 변경"
        )
    lines.append("실험 묶음: 변인 통제 v2 (GRID_N=12, MAX_ANGULAR_VEL=2, RESTITUTION=0.15)")
    return lines


def _controlled_caption_ko(group: str, x0: float, radius: float, factor: float) -> str:
    """밀도 차트 제목용 변인 통제 한 줄 설명."""
    rho = _fmt_factor(factor)
    if group == "factor":
        return f"변인: {rho} (편심x좌표={x0:g}, 반지름={radius:g} 일정)"
    if group == "radius":
        return f"변인: 반지름={radius:g} (편심x좌표={x0:g}, {rho} 일정)"
    if group == "center":
        return f"변인: 편심x좌표={x0:g} (반지름={radius:g}, {rho} 일정)"
    return ""


def _group_header_from_spec(spec: dict) -> str:
    """변인 그룹 헤더 — 고정 조건만, 변인 값은 제외."""
    g = spec["group"]
    x0, r, f = spec["x0"], spec["radius"], spec["factor"]
    rho = _fmt_factor(f)
    if g == "factor":
        return f"변인: ρ (편심x좌표={x0:g}, 반지름={r:g} 일정)"
    if g == "radius":
        return f"변인: 반지름 (편심x좌표={x0:g}, {rho} 일정)"
    if g == "center":
        return f"변인: 편심x좌표 (반지름={r:g}, {rho} 일정)"
    return spec.get("name", "")


def variable_group_header_ko(study_id: str | None, variable_group: str) -> str:
    """대시보드 변인 그룹 헤더."""
    from simulation.output_layout import reference_spec_for_group

    if variable_group == "uniform":
        return "기준선 — 균일 밀도 ρ=1"
    if variable_group == "legacy":
        return "구 밀도 실험"

    spec = reference_spec_for_group(study_id or "", variable_group) if study_id else None
    if spec:
        return _group_header_from_spec(spec)

    labels = {
        "factor": "변인: ρ",
        "radius": "변인: 반지름",
        "center": "변인: 편심 x좌표",
    }
    return labels.get(variable_group, variable_group)


def preset_display_label_ko(rho_name: str) -> str:
    """사이드바·내비용 짧은 라벨 (변인 값만)."""
    if rho_name == "uniform":
        return "ρ=1"

    spec = lookup_controlled_spec(rho_name)
    if spec:
        g = spec["group"]
        if g == "factor":
            return _fmt_factor(spec["factor"])
        if g == "radius":
            return _fmt_radius(spec["radius"])
        if g == "center":
            return _fmt_x0(spec["x0"])

    for spec in SPHERE_STUDY_SPECS:
        if spec["name"] == rho_name:
            return _fmt_factor(spec["factor"])

    if rho_name.startswith("ctrl_factor_f"):
        f = _parse_name_f(rho_name.replace("ctrl_factor_f", ""))
        return _fmt_factor(f)
    if rho_name.startswith("ctrl_radius_r"):
        r = _parse_name_r(rho_name.replace("ctrl_radius_r", ""))
        return _fmt_radius(r)
    if rho_name.startswith("ctrl_center_x"):
        x = _parse_name_x(rho_name.replace("ctrl_center_x", ""))
        return _fmt_x0(x)
    return rho_name


def export_png_filename_ko(
    rho_name: str,
    chart: str,
    *,
    n_trials: int | None = None,
) -> str:
    """ZIP 내부 PNG 파일명 (확장자 제외)."""
    prefix = "확률" if chart == "prob" else "질량"

    if rho_name == "uniform":
        if chart == "prob" and n_trials:
            return f"{prefix}_균일 (N={n_trials})"
        return f"{prefix}_균일"

    spec = lookup_controlled_spec(rho_name)
    if spec:
        g = spec["group"]
        x0, r, f = spec["x0"], spec["radius"], spec["factor"]
        sx = f"편심{x0:g}"
        sr = f"반지름{r:g}"
        sd = f"밀도{f:g}"
        if g == "factor":
            head, tail = sd, f"{sx} {sr}"
        elif g == "radius":
            head, tail = sr, f"{sx} {sd}"
        elif g == "center":
            head, tail = sx, f"{sr} {sd}"
        else:
            head, tail = rho_name, ""
        if chart == "prob" and n_trials:
            return f"{prefix}_{head} ({tail} N={n_trials})"
        return f"{prefix}_{head} ({tail})"

    for spec in SPHERE_STUDY_SPECS:
        if spec["name"] == rho_name:
            head = f"밀도{spec['factor']:g}"
            tail = f"편심{spec['x0']:g} 반지름{spec['radius']:g}"
            if chart == "prob" and n_trials:
                return f"{prefix}_{head} ({tail} N={n_trials})"
            return f"{prefix}_{head} ({tail})"

    if chart == "prob" and n_trials:
        return f"{prefix}_{rho_name} (N={n_trials})"
    return f"{prefix}_{rho_name}"


def _preset_plot_subtitle_ko(rho_name: str) -> str:
    """차트 제목 아래 줄 — 고정 조건."""
    if rho_name == "uniform":
        return "(균일 밀도)"

    spec = lookup_controlled_spec(rho_name)
    if spec:
        g = spec["group"]
        x0, r, f = spec["x0"], spec["radius"], spec["factor"]
        rho = _fmt_factor(f)
        if g == "factor":
            return f"(편심x좌표={x0:g}, 반지름={r:g} 일정)"
        if g == "radius":
            return f"(편심x좌표={x0:g}, {rho} 일정)"
        if g == "center":
            return f"(반지름={r:g}, {rho} 일정)"

    for spec in SPHERE_STUDY_SPECS:
        if spec["name"] == rho_name:
            return (
                f"(반지름={spec['radius']:g}, "
                f"{_fmt_x0(spec['x0'])})"
            )
    return ""


def preset_short_caption_ko(rho_name: str) -> str:
    """밀도 차트 제목용 한 줄 변인 설명."""
    if rho_name == "uniform":
        return "균일 밀도 ρ=1 — 공정 주사위 기준"

    for spec in ALL_CONTROLLED_SPECS:
        if spec["name"] != rho_name:
            continue
        g = spec["group"]
        return _controlled_caption_ko(g, spec["x0"], spec["radius"], spec["factor"])

    for spec in SPHERE_STUDY_SPECS:
        if spec["name"] == rho_name:
            return (
                f"구 밀도 실험: +x bump {_fmt_radius(spec['radius'])}, "
                f"{_fmt_factor(spec['factor'])}, {_fmt_x0(spec['x0'])}"
            )

    if rho_name.startswith("ctrl_factor_f"):
        f = _parse_name_f(rho_name.replace("ctrl_factor_f", ""))
        return f"변인: {_fmt_factor(f)} (편심x좌표·반지름 일정)"
    if rho_name.startswith("ctrl_radius_r"):
        r = _parse_name_r(rho_name.replace("ctrl_radius_r", ""))
        return f"변인: 반지름={r:g} (편심x좌표·ρ 일정)"
    if rho_name.startswith("ctrl_center_x"):
        x = _parse_name_x(rho_name.replace("ctrl_center_x", ""))
        return f"변인: 편심x좌표={x:g} (반지름·ρ 일정)"
    if rho_name.startswith("sphere_"):
        return f"구형 bump 비대칭 밀도 ({rho_name})"
    return ""


def _plotly_stacked_title(
    main_line: str,
    sub_line: str,
    *,
    main_size: int = 16,
    sub_size: int = 11,
) -> str:
    """Plotly 제목: 위 큰 줄 + 아래 작은 줄."""
    return (
        f"<span style='font-size:{main_size}px;font-weight:600'>{main_line}</span>"
        f"<br><span style='font-size:{sub_size}px;color:#64748b'>{sub_line}</span>"
    )


def density_plot_title_lines(rho_name: str) -> tuple[str, str | None]:
    """질량분포 차트 제목 2줄."""
    varying, fixed = _preset_varying_and_fixed(rho_name)
    line1 = f"주사위의 질량 분포 ({varying})"
    line2 = f"({fixed})" if fixed else None
    return line1, line2


def density_plot_title(rho_name: str) -> tuple[str, str | None]:
    """Plotly 질량분포 제목 줄 (하위 호환 이름)."""
    return density_plot_title_lines(rho_name)


def _preset_varying_and_fixed(rho_name: str) -> tuple[str, str | None]:
    """차트 제목용 — (변인 줄, 고정 조건 줄·괄호 없음)."""
    spec = lookup_controlled_spec(rho_name)
    if spec:
        g = spec["group"]
        x0, r, f = spec["x0"], spec["radius"], spec["factor"]
        if g == "factor":
            return _fmt_density(spec["factor"]), f"편심 x좌표={x0:g}, 반지름={r:g} 일정"
        if g == "radius":
            return _fmt_radius(r), f"편심 x좌표={x0:g}, {_fmt_density(f)} 일정"
        if g == "center":
            return _fmt_x0_prob(x0), f"반지름={r:g}, {_fmt_density(f)} 일정"

    if rho_name == "uniform":
        return "밀도=1", "균일 밀도"

    varying = preset_display_label_ko(rho_name)
    sub = _preset_plot_subtitle_ko(rho_name)
    fixed = sub.strip("()") if sub else None
    return varying, fixed


def _probability_title_lines(
    rho_name: str,
    n_trials: int,
    *,
    cancelled: bool = False,
    target_trials: int | None = None,
) -> tuple[str, str]:
    """확률 차트 제목 2줄."""
    if cancelled and target_trials is not None:
        n_part = f"N={n_trials:,}/{target_trials:,} (중단)"
    else:
        n_part = f"N={n_trials:,}"

    varying, fixed = _preset_varying_and_fixed(rho_name)
    line1 = f"바닥의 눈의 확률분포 ({varying})"
    if fixed:
        line2 = f"({fixed}, {n_part})"
    else:
        line2 = f"({n_part})"
    return line1, line2


def probability_plot_title(
    rho_name: str,
    n_trials: int,
    *,
    cancelled: bool = False,
    target_trials: int | None = None,
) -> tuple[str, str | None]:
    """Plotly 확률분포 제목 2줄."""
    return _probability_title_lines(
        rho_name,
        n_trials,
        cancelled=cancelled,
        target_trials=target_trials,
    )


def preset_density_lines(rho_name: str) -> list[str]:
    """프리셋 이름만으로 밀도 조건 설명."""
    if rho_name == "uniform":
        return _uniform_lines()

    spec = lookup_controlled_spec(rho_name)
    if spec:
        return _controlled_spec_lines(spec)

    for spec in SPHERE_STUDY_SPECS:
        if spec["name"] == rho_name:
            lines = _sphere_spec_lines(spec)
            lines.append("실험 묶음: 구 밀도 실험 (sphere_legacy)")
            return lines

    if rho_name.startswith("ctrl_factor_f"):
        f = _parse_name_f(rho_name.replace("ctrl_factor_f", ""))
        return [
            f"구형 고밀도 영역 ({_fmt_factor(f)}, 상세 좌표는 스펙 참고)",
            f"변인 통제(구형) 밀도 프리셋 — {_fmt_factor(f)} (v1 또는 미등록 스펙)",
        ]
    if rho_name.startswith("ctrl_radius_r"):
        r = _parse_name_r(rho_name.replace("ctrl_radius_r", ""))
        return [f"변인 통제(구형) 반지름 프리셋 — {_fmt_radius(r)}"]
    if rho_name.startswith("ctrl_center_x"):
        x = _parse_name_x(rho_name.replace("ctrl_center_x", ""))
        return [f"변인 통제(구형) 중심 프리셋 — {_fmt_x0(x)}"]
    if rho_name.startswith("sphere_"):
        return [f"구형 bump 프리셋: {rho_name} (상세 스펙은 SPHERE_STUDY_SPECS 참고)"]

    return [f"사용자/기타 프리셋: {rho_name}"]


def study_label_ko(study_id: str | None) -> str | None:
    from simulation.output_layout import STUDY_LABELS

    if not study_id:
        return None
    return STUDY_LABELS.get(study_id, study_id)


def build_conditions(item: dict) -> dict[str, Any]:
    """
    대시보드 항목용 한국어 조건 블록.

    item: flatten_group_items()의 원소 (simulation 또는 preview)
    """
    rho_name = item.get("rho_name") or item.get("label", "?")
    sections: list[dict[str, Any]] = [
        {"title": "밀도 조건", "lines": preset_density_lines(rho_name)},
        {"title": "공통 물리·시뮬 설정", "lines": global_physics_lines()},
    ]

    if item.get("kind") == "simulation":
        run_lines = []
        if item.get("run_id"):
            run_lines.append(f"실행 ID: {item['run_id']}")
        if item.get("timestamp"):
            run_lines.append(f"저장 시각: {item['timestamp'][:19].replace('T', ' ')}")
        n = item.get("n_trials") or 0
        target = item.get("target_trials") or n
        if item.get("cancelled"):
            run_lines.append(f"시행 횟수: {n:,} / {target:,} (중단됨)")
        else:
            run_lines.append(f"시행 횟수 (몬테카를로): {n:,}회")
        sid = item.get("study_id")
        slabel = study_label_ko(sid)
        if slabel:
            run_lines.append(f"실험 묶음: {slabel}")
        vg = item.get("variable_group")
        if vg:
            run_lines.append(f"변인 그룹: {variable_group_header_ko(sid, vg)}")
        if item.get("top_face"):
            run_lines.append(
                f"이 실행 최다 바닥 면: 눈 {item['top_face']} "
                f"({float(item.get('top_p', 0)) * 100:.2f}%)"
            )
        sections.append({"title": "이 시뮬레이션 실행", "lines": run_lines})
    else:
        sections.append(
            {
                "title": "이 항목",
                "lines": [
                    "유형: 설계 단계 밀도 미리보기 (시뮬 전)",
                    "확률분포 탭 없음 — 질량분포 HTML만 존재",
                ],
            }
        )

    summary_parts = [rho_name]
    if item.get("kind") == "simulation" and item.get("n_trials"):
        summary_parts.append(f"N={item['n_trials']:,}")
    if item.get("study_label"):
        summary_parts.insert(0, item["study_label"])
    if item.get("variable_group_label"):
        summary_parts.insert(0, item["variable_group_label"])

    return {
        "summary": " · ".join(summary_parts),
        "sections": sections,
    }


def enrich_items_with_conditions(items: list[dict]) -> list[dict]:
    """각 항목에 conditions 필드 추가."""
    out = []
    for item in items:
        enriched = {**item, "conditions": build_conditions(item)}
        out.append(enriched)
    return out
