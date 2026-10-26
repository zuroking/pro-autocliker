from __future__ import annotations

import random
import threading
import time
from typing import Callable, Optional

from pynput.mouse import Button

from .config import ButtonName, ClickConfig, ClickTypeName, MouseController

BUTTON_MAP: dict[ButtonName, Button] = {
    "left": Button.left,
    "right": Button.right,
    "middle": Button.middle,
}


class ClickEngine:
    """Runs a single click stream on a daemon thread."""

    def __init__(
        self,
        config: ClickConfig,
        mouse: MouseController,
        on_status: Optional[Callable[[str], None]] = None,
        mouse_lock: Optional[threading.Lock] = None,
    ) -> None:
        self.config = config
        self.mouse = mouse
        self.on_status = on_status or (lambda _msg: None)
        self._mouse_lock = mouse_lock or threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._clicks_done = 0

    @property
    def clicks_done(self) -> int:
        return self._clicks_done

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop.clear()
        self._clicks_done = 0
        self._thread = threading.Thread(target=self._run, name="click-engine", daemon=True)
        self._thread.start()
        self._emit("started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._emit("stopped")

    def _emit(self, msg: str) -> None:
        try:
            self.on_status(msg)
        except Exception:
            pass

    def _sleep(self, seconds: float) -> bool:
        """Return True if woken by stop event."""
        return self._stop.wait(seconds)

    def _do_click(self, btn: Button) -> None:
        cfg = self.config
        if cfg.click_type == "hold":
            with self._mouse_lock:
                self.mouse.press(btn)
            self._sleep(cfg.hold_duration_ms / 1000.0)
            with self._mouse_lock:
                self.mouse.release(btn)
        elif cfg.click_type == "double":
            with self._mouse_lock:
                self.mouse.click(btn, 2)
        else:
            with self._mouse_lock:
                self.mouse.click(btn, 1)

    def _run(self) -> None:
        cfg = self.config
        btn = BUTTON_MAP[cfg.button]
        target_count = cfg.count  # 0 = infinite
        original_pos: Optional[tuple[int, int]] = None

        try:
            while not self._stop.is_set():
                if target_count and self._clicks_done >= target_count:
                    break

                # fixed position handling
                if cfg.mode == "fixed":
                    with self._mouse_lock:
                        original_pos = self.mouse.position
                        self.mouse.position = (cfg.x, cfg.y)
                    self._do_click(btn)
                    if cfg.restore_cursor and original_pos is not None:
                        with self._mouse_lock:
                            self.mouse.position = original_pos
                else:
                    self._do_click(btn)

                self._clicks_done += 1
                self._emit(f"click {self._clicks_done}")

                if target_count and self._clicks_done >= target_count:
                    break

                # wait interval with jitter
                base = cfg.interval_ms / 1000.0
                jitter = cfg.interval_jitter_ms / 1000.0
                if jitter > 0:
                    delta = random.uniform(-jitter, jitter)
                else:
                    delta = 0.0
                wait_s = max(0.0, base + delta)
                if self._sleep(wait_s):
                    break
        except Exception as exc:  # pragma: no cover - defensive
            self._emit(f"error: {exc}")
        finally:
            self._stop.set()
            self._emit("finished")