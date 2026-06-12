"""6×6×6 밀도 격자 — 주사위 내부를 작은 상자들로 나눈 데이터."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from config import DIE_HALF_SIZE, GRID_N


class RhoGrid:
    """
    주사위 [-half, half]³ 를 n×n×n 소셀로 나누고, 각 소셀에 밀도 ρ를 저장합니다.

    비유: 케이크를 6×6×6 조각으로 자르고, 각 조각이 얼마나 무거운지 적어 둔 것.
    """

    def __init__(self, rho: np.ndarray, n: int = GRID_N, half_size: float = DIE_HALF_SIZE):
        rho = np.asarray(rho, dtype=float)
        if rho.shape != (n, n, n):
            raise ValueError(f"rho shape must be ({n},{n},{n}), got {rho.shape}")
        if np.any(rho < 0):
            raise ValueError("밀도는 0 이상이어야 합니다.")

        self.rho = rho
        self.n = n
        self.half_size = half_size
        self.cell_size = (2 * half_size) / n
        self.cell_volume = self.cell_size**3

    @property
    def cell_centers(self) -> np.ndarray:
        """각 소셀 중심의 (x,y,z) 좌표 — shape (n,n,n,3)."""
        axis = np.linspace(
            -self.half_size + self.cell_size / 2,
            self.half_size - self.cell_size / 2,
            self.n,
        )
        xx, yy, zz = np.meshgrid(axis, axis, axis, indexing="ij")
        return np.stack([xx, yy, zz], axis=-1)

    @property
    def total_mass(self) -> float:
        """총 질량 M = Σ ρ × (소셀 부피)."""
        return float(np.sum(self.rho) * self.cell_volume)

    @property
    def center_of_mass(self) -> np.ndarray:
        """
        무게중심 (질량 중심).

        공식: r_cm = (Σ m_i × r_i) / (Σ m_i)
        균일 밀도면 원점 (0,0,0)에 가깝습니다.
        """
        masses = self.rho * self.cell_volume
        total = np.sum(masses)
        if total == 0:
            return np.zeros(3)
        weighted = self.cell_centers * masses[..., np.newaxis]
        return np.sum(weighted, axis=(0, 1, 2)) / total

    def save(self, path: str | Path) -> None:
        np.save(path, self.rho)

    @classmethod
    def load(cls, path: str | Path, n: int = GRID_N) -> "RhoGrid":
        rho = np.load(path)
        return cls(rho, n=n)

    def __repr__(self) -> str:
        return (
            f"RhoGrid(n={self.n}, mass={self.total_mass:.4f}, "
            f"com={self.center_of_mass.round(4)})"
        )
