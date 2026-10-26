from __future__ import annotations

import threading
from typing import Any


class FakeMouse:
    def __init__(self) -> None:
        self.position = (0, 0)
        self.clicks: list[tuple[Any, int]] = []
        self.presses: list[Any] = []
        self.releases: list[Any] = []
        self._lock = threading.Lock()

    def click(self, button: Any, count: int = 1) -> None:
        with self._lock:
            self.clicks.append((button, count))

    def press(self, button: Any) -> None:
        with self._lock:
            self.presses.append(button)

    def release(self, button: Any) -> None:
        with self._lock:
            self.releases.append(button)

    def scroll(self, dx: int, dy: int) -> None:
        pass