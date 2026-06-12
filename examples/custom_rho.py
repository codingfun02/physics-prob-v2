"""
사용자 정의 밀도 함수 예제.

사용법:
    conda activate physics-prob-v2
    python examples/custom_rho.py

또는 main.py에서 만든 .npy 파일 사용:
    python main.py --rho-file output/custom_rho.npy --trials 5000
"""

from pathlib import Path

from density.analytic import discretize_rho
from density.visualize import plot_rho_grid


def my_rho(x: float, y: float, z: float) -> float:
    """
    원하는 밀도 함수를 여기에 작성하세요.
    예: 오른쪽 위 앞 모서리가 무거운 주사위
    """
    return 1.0 + 3.0 * x + 2.0 * z


def main():
    grid = discretize_rho(my_rho)
    print(grid)

    out = Path("output")
    out.mkdir(exist_ok=True)
    grid.save(out / "custom_rho.npy")
    plot_rho_grid(grid, title="사용자 정의 ρ", save_path=out / "custom_rho_density.html", show=False)
    print(f"저장됨: {out / 'custom_rho.npy'}")
    print(f"시뮬 실행: python main.py --rho-file output/custom_rho.npy --trials 5000")


if __name__ == "__main__":
    main()
