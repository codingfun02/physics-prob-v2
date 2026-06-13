"""시뮬레이션 중 Ctrl+C로 안전하게 중단."""

from __future__ import annotations

import signal
import sys
import threading

_cancel = threading.Event()
_handler_installed = False


def is_cancel_requested() -> bool:
    return _cancel.is_set()


def request_cancel() -> None:
    _cancel.set()


def reset_cancel() -> None:
    _cancel.clear()


def install_cancel_handler() -> None:
    """Ctrl+C 1회: 중단 요청, 2회: 즉시 종료."""
    global _handler_installed
    if _handler_installed:
        return

    def _on_sigint(signum, frame):
        if not is_cancel_requested():
            request_cancel()
            print(
                "\n[중단 요청] 현재 시행을 마친 뒤 저장하고 종료합니다. "
                "(즉시 끝내려면 Ctrl+C를 한 번 더 누르세요)",
                file=sys.stderr,
            )
        else:
            print("\n[즉시 종료]", file=sys.stderr)
            raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _on_sigint)
    _handler_installed = True
