"""몬테카를로 진행률 표시 — 초기 워커 기동 시 ETA 왜곡 방지."""

from __future__ import annotations

import time

from tqdm import tqdm


def _format_duration(seconds: float) -> str:
    """초 → MM:SS 또는 HH:MM:SS."""
    seconds = max(0.0, seconds)
    s = int(seconds + 0.5)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


class MonteCarloProgress:
    """
    tqdm 래퍼: 워커 초기화·첫 배치가 느릴 때 남은 시간이 경과보다 크게 나오는 문제를 완화.

    - 워밍업 구간: 남은 시간 대신 '측정 중'
    - 이후: 경과 / 남은 시간을 항상 elapsed <= remaining 이 되도록 표시하지 않고,
      평균 속도 기반 ETA를 별도 계산 (단조적으로 현실적인 값)
    """

    def __init__(self, total: int, desc: str = "시뮬레이션", warmup: int | None = None):
        self.total = total
        self.warmup = warmup if warmup is not None else max(100, total // 200)
        self._t0 = time.perf_counter()
        self._pbar = tqdm(
            total=total,
            desc=desc,
            bar_format="{desc}: {n_fmt}/{total_fmt} |{bar}| [{elapsed}, {postfix}]",
            smoothing=0.0,
        )

    def update(self, n: int = 1) -> None:
        self._pbar.update(n)
        done = self._pbar.n
        elapsed = time.perf_counter() - self._t0

        if done < self.warmup:
            self._pbar.set_postfix_str("남은 시간: 측정 중…", refresh=True)
            return

        rate = done / elapsed if elapsed > 0 else 0.0
        if rate <= 0:
            self._pbar.set_postfix_str("남은 시간: —", refresh=True)
            return

        remaining = (self.total - done) / rate
        # 경과보다 남은 시간이 비정상적으로 짧아졌다가 튀는 경우 방지:
        # ETA는 최소 0, 표시는 elapsed와 독립적으로 평균 속도만 사용
        self._pbar.set_postfix_str(
            f"남은 시간: ~{_format_duration(remaining)}  ({rate:.1f} 회/초)",
            refresh=True,
        )

    def close(self) -> None:
        self._pbar.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
