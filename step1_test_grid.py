"""1단계 테스트: 균일 밀도 격자가 잘 만들어지는지 확인."""

from density.analytic import get_preset_rho
from density.visualize import plot_rho_grid

grid = get_preset_rho("uniform")
print("=== 1단계 결과 ===")
print(grid)
print(f"밀도 범위: {grid.rho.min()} ~ {grid.rho.max()}")
print(f"무게중심 (0,0,0에 가까워야 함): {grid.center_of_mass}")

plot_rho_grid(grid, title="균일 밀도 (검증용)", show=False)
print("3D 그래프 저장됨: output/rho_density.html")
