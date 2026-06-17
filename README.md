# physics_prob_distribution_v2

비균일 밀도 정육면체 주사위의 **바닥 면** 확률분포를 PyBullet 몬테카를로로 추정합니다.

## 환경 설정

conda activate physics-prob-v2

## 빠른 시작

python step1_test_grid.py
python main.py --single-test
python main.py --rho uniform --trials 50000 --workers 4
python step4_validation.py

## PyBullet GUI (균일 밀도 1회 던지기)

```bat
run.bat prototype_throw_viewer.py
```

우측 Params **Throw (1x)** 버튼 또는 **T** 키로 주사위를 던집니다.

## 보고서용 차트 병합 (변인 그룹별 3×2)

```bat
run.bat merge_report_panels.py
```

`factor` / `radius` / `center` 그룹마다 확률 3개(위) + 질량 3개(아래)를 하나의 PNG로 저장합니다.
`uniform` 그룹은 1×2(왼쪽 확률, 오른쪽 질량)로 저장합니다.
출력: `output/png/merged__controlled_v3__{group}.png`, `docs/report_panels/` (복사본)

## 문서

[docs/density_to_simulation_guide.html](docs/density_to_simulation_guide.html) — 밀도·관성·PyBullet 시뮬·확률 추정 통합 가이드 (v3 기준)
