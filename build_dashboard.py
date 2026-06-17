"""대시보드 HTML 생성 및 기존 확률 차트 갱신."""

from __future__ import annotations

import argparse

from config import OUTPUT_DIR
from simulation.dashboard import build_dashboard, refresh_density_htmls, refresh_probability_charts


def main():
    parser = argparse.ArgumentParser(description="결과 대시보드 HTML 생성")
    parser.add_argument(
        "--refresh-charts",
        action="store_true",
        help="확률 HTML·PNG를 study별 통일 y축으로 다시 생성",
    )
    parser.add_argument(
        "--study",
        default=None,
        help="--refresh-charts 시 특정 study만 (예: controlled_v3)",
    )
    parser.add_argument(
        "--refresh-density",
        action="store_true",
        help="밀도 HTML에 눈(1~6) 라벨 포함하여 다시 생성",
    )
    parser.add_argument(
        "--reorganize",
        action="store_true",
        help="기존 output/ 폴더를 정리된 구조로 이전·중복 삭제",
    )
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    args = parser.parse_args()

    if args.reorganize:
        from simulation.output_layout import reorganize_output

        stats = reorganize_output(args.output_dir)
        print(
            f"정리 완료: 이동 {stats['moved']}개, 삭제 {stats['deleted']}개"
        )

    if args.refresh_charts:
        n = refresh_probability_charts(
            args.output_dir,
            only_stale=False,
            study_id=args.study,
        )
        print(f"확률 차트 {n}개 갱신")

    if args.refresh_density:
        n = refresh_density_htmls(args.output_dir, only_stale=False)
        print(f"밀도 HTML {n}개 갱신")

    path = build_dashboard(args.output_dir)
    print(f"대시보드 저장: {path.resolve()}")
    print("브라우저에서 열어 runs 결과를 탐색하세요.")


if __name__ == "__main__":
    main()
