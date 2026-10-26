from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from pynput import keyboard as kb
from pynput import mouse as ms

from .config import Macro, MacroEvent


class MacroRecorder:
    """Records mouse (and optionally keyboard) events with relative timestamps."""

    def __init__(self, record_keyboard: bool = False) -> None:
        self.record_keyboard = record_keyboard
        self._events: list[MacroEvent] = []
        self._start: Optional[float] = None
        self._mouse_listener: Optional[ms.Listener] = None
        self._kb_listener: Optional[kb.Listener] = None
        self._lock = threading.Lock()

    @property
    def events(self) -> list[MacroEvent]:
        with self._lock:
            return list(self._events)

    def start(self) -> None:
        with self._lock:
            self._events = []
        self._start = time.perf_counter()
        self._mouse_listener = ms.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._mouse_listener.start()
        if self.record_keyboard:
            self._kb_listener = kb.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
            )
            self._kb_listener.start()

    def stop(self) -> list[MacroEvent]:
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._kb_listener is not None:
            self._kb_listener.stop()
            self._kb_listener = None
        with self._lock:
            return list(self._events)

    def _t(self) -> int:
        assert self._start is not None
        return int((time.perf_counter() - self._start) * 1000)

    def _on_move(self, x: int, y: int) -> None:
        with self._lock:
            self._events.append(MacroEvent(t_ms=self._t(), kind="move", data={"x": x, "y": y}))

    def _on_click(self, x: int, y: int, button: ms.Button, pressed: bool) -> None:
        with self._lock:
            self._events.append(
                MacroEvent(
                    t_ms=self._t(),
                    kind="click" if pressed else "release",
                    data={"x": x, "y": y, "button": str(button)},
                )
            )

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        with self._lock:
            self._events.append(
                MacroEvent(t_ms=self._t(), kind="scroll", data={"x": x, "y": y, "dx": dx, "dy": dy})
            )

    def _on_key_press(self, key: Any) -> None:
        with self._lock:
            self._events.append(MacroEvent(t_ms=self._t(), kind="key", data={"action": "press", "key": str(key)}))

    def _on_key_release(self, key: Any) -> None:
        with self._lock:
            self._events.append(MacroEvent(t_ms=self._t(), kind="key", data={"action": "release", "key": str(key)}))


class MacroPlayer:
    """Replays a Macro with original (scaled) timing."""

    def __init__(self, macro: Macro, mouse: ms.Controller, keyboard: kb.Controller) -> None:
        self.macro = macro
        self.mouse = mouse
        self.keyboard = keyboard
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, on_status: Optional[Callable[[str], None]] = None) -> None:
        if self.is_running:
            return
        self._stop.clear()
        cb = on_status or (lambda _m: None)
        self._thread = threading.Thread(target=self._run, args=(cb,), name="macro-player", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            if not self._thread.is_alive():
                self._thread = None

    def _run(self, cb: Callable[[str], None]) -> None:
        try:
            events = sorted(self.macro.events, key=lambda e: e.t_ms)
            speed = self.macro.speed
            prev_t = 0
            for ev in events:
                if self._stop.is_set():
                    break
                delay = (ev.t_ms - prev_t) / 1000.0 / speed
                if delay > 0:
                    if self._stop.wait(delay):
                        break
                self._apply(ev)
                prev_t = ev.t_ms
            if not self._stop.is_set():
                cb("macro finished")
        except Exception as exc:  # pragma: no cover
            cb(f"macro error: {exc}")
        finally:
            self._stop.set()

    def _apply(self, ev: MacroEvent) -> None:
        d = ev.data
        if ev.kind == "move":
            self.mouse.position = (int(d["x"]), int(d["y"]))
        elif ev.kind == "click":
            btn = _btn(d.get("button", "Button.left"))
            self.mouse.position = (int(d["x"]), int(d["y"]))
            self.mouse.click(btn, 1)
        elif ev.kind == "press":
            btn = _btn(d.get("button", "Button.left"))
            self.mouse.press(btn)
        elif ev.kind == "release":
            btn = _btn(d.get("button", "Button.left"))
            self.mouse.release(btn)
        elif ev.kind == "scroll":
            self.mouse.scroll(int(d.get("dx", 0)), int(d.get("dy", 0)))
        elif ev.kind == "key":
            pass  # keyboard replay omitted in v0.1 for safety


def _btn(name: str) -> ms.Button:
    mapping = {"Button.left": ms.Button.left, "Button.right": ms.Button.right, "Button.middle": ms.Button.middle}
    return mapping.get(name, ms.Button.left)