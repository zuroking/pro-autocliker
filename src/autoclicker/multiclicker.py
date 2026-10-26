from __future__ import annotations

import threading
from typing import Callable, Optional

from pynput.mouse import Controller as MouseControllerImpl

from .config import ClickConfig, MouseController
from .engine import ClickEngine


class MultiClicker:
    """Orchestrates up to max_streams independent click engines."""

    def __init__(self, max_streams: int = 8, on_status: Optional[Callable[[str], None]] = None) -> None:
        self.max_streams = max_streams
        self.on_status = on_status or (lambda _m: None)
        self._mouse = MouseControllerImpl()
        self._lock = threading.Lock()
        self._engines: list[ClickEngine] = []

    @property
    def engines(self) -> list[ClickEngine]:
        return list(self._engines)

    def add(self, config: ClickConfig) -> Optional[ClickEngine]:
        if len(self._engines) >= self.max_streams:
            self.on_status("max streams reached")
            return None
        eng = ClickEngine(config, self._mouse, on_status=self.on_status, mouse_lock=self._lock)
        self._engines.append(eng)
        return eng

    def remove(self, index: int) -> None:
        if 0 <= index < len(self._engines):
            eng = self._engines.pop(index)
            if eng.is_running:
                eng.stop()

    def start_all(self) -> None:
        for eng in self._engines:
            eng.start()

    def stop_all(self) -> None:
        for eng in self._engines:
            eng.stop()

    def clear(self) -> None:
        self.stop_all()
        self._engines.clear()