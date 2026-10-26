from __future__ import annotations

import threading
from typing import Callable, Optional

from pynput import keyboard

from .config import HotkeyBindings


class HotkeyManager:
    def __init__(self, bindings: HotkeyBindings) -> None:
        self.bindings = bindings
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._callbacks: dict[str, Callable[[], None]] = {}

    def register(self, name: str, cb: Callable[[], None]) -> None:
        self._callbacks[name] = cb

    def start(self) -> None:
        if self._listener is not None:
            return
        mapping: dict[str, Callable[[], None]] = {}
        b = self.bindings
        if "start_stop" in self._callbacks:
            mapping[f"<{b.start_stop}>"] = self._callbacks["start_stop"]
        if "record_macro" in self._callbacks:
            mapping[f"<{b.record_macro}>"] = self._callbacks["record_macro"]
        if "emergency_stop" in self._callbacks:
            mapping[f"<{b.emergency_stop}>"] = self._callbacks["emergency_stop"]
        self._listener = keyboard.GlobalHotKeys(mapping)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None