from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from pynput.mouse import Button

from .config import MouseController

BUTTONS = {"left": Button.left, "right": Button.right, "middle": Button.middle}


@dataclass
class Stmt:
    kind: str
    args: list[str] = field(default_factory=list)
    body: list["Stmt"] = field(default_factory=list)
    lineno: int = 0


class ScriptError(Exception):
    def __init__(self, lineno: int, msg: str) -> None:
        super().__init__(f"line {lineno}: {msg}")
        self.lineno = lineno


def parse(source: str) -> list[Stmt]:
    lines = source.splitlines()
    # strip comments and blanks
    cleaned: list[tuple[int, str]] = []
    for i, raw in enumerate(lines, start=1):
        s = raw.split("#", 1)[0].rstrip()
        if s.strip() == "":
            continue
        cleaned.append((i, s))
    return _parse_block(cleaned, 0)[0]


def _indent_level(s: str) -> int:
    return len(s) - len(s.lstrip(" "))


def _parse_block(items: list[tuple[int, str]], start: int) -> tuple[list[Stmt], int]:
    stmts: list[Stmt] = []
    i = start
    n = len(items)
    while i < n:
        lineno, text = items[i]
        stripped = text.strip()
        level = _indent_level(text)
        # if we are inside a block, deeper indent belongs to parent; handle in loop caller
        # top-level / same level handling:
        if stripped.startswith("loop "):
            m = re.match(r"loop\s+(\d+)\s*\{?\s*$", stripped)
            if not m:
                raise ScriptError(lineno, "expected 'loop N {'")
            count = int(m.group(1))
            # expect '{' either inline or next
            i += 1
            body_items: list[tuple[int, str]] = []
            # collect indented or braced body
            if stripped.endswith("{"):
                # braced: collect until matching '}'
                depth = 1
                while i < n and depth > 0:
                    ln, tx = items[i]
                    st = tx.strip()
                    if st == "}":
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                        i += 1
                        continue
                    if st.endswith("{"):
                        depth += 1
                    body_items.append((ln, tx))
                    i += 1
                body = _parse_block(body_items, 0)[0]
            else:
                # indented body: collect lines with greater indent
                base_level = _indent_level(items[i - 1][1]) if i > 0 else 0
                # determine body indent from first non-empty
                body_level = None
                while i < n:
                    ln, tx = items[i]
                    if _indent_level(tx) <= base_level:
                        break
                    if body_level is None:
                        body_level = _indent_level(tx)
                    body_items.append((ln, tx))
                    i += 1
                body = _parse_block(body_items, 0)[0]
            stmts.append(Stmt(kind="loop", args=[str(count)], body=body, lineno=lineno))
            continue
        if stripped == "}":
            i += 1
            continue
        stmts.append(_parse_simple(stripped, lineno))
        i += 1
    return stmts, i


def _parse_simple(text: str, lineno: int) -> Stmt:
    parts = text.split()
    if not parts:
        raise ScriptError(lineno, "empty statement")
    cmd = parts[0].lower()
    if cmd in ("click", "doubleclick", "hold"):
        # click [button] [at x,y]
        return Stmt(kind=cmd, args=parts[1:], lineno=lineno)
    if cmd == "move":
        return Stmt(kind="move", args=parts[1:], lineno=lineno)
    if cmd == "wait":
        return Stmt(kind="wait", args=parts[1:], lineno=lineno)
    raise ScriptError(lineno, f"unknown command '{cmd}'")


class ScriptRunner:
    def __init__(self, mouse: MouseController, on_status: Optional[Callable[[str], None]] = None) -> None:
        self.mouse = mouse
        self.on_status = on_status or (lambda _m: None)
        self.stop_event = threading.Event()

    def run(self, source: str) -> None:
        import threading

        self.stop_event = threading.Event()
        try:
            stmts = parse(source)
        except ScriptError as e:
            self.on_status(str(e))
            return
        threading.Thread(target=self._exec_block, args=(stmts,), name="script-runner", daemon=True).start()

    def stop(self) -> None:
        self.stop_event.set()

    def _exec_block(self, stmts: list[Stmt]) -> None:
        for st in stmts:
            if self.stop_event.is_set():
                break
            try:
                self._exec(st)
            except Exception as e:
                self.on_status(f"line {st.lineno}: {e}")
                break

    def _exec(self, st: Stmt) -> None:
        if st.kind == "loop":
            n = int(st.args[0])
            for _ in range(n):
                if self.stop_event.is_set():
                    break
                self._exec_block(st.body)
            return
        if st.kind == "wait":
            ms = int(st.args[0])
            self.stop_event.wait(ms / 1000.0)
            return
        if st.kind == "move":
            x, y = _parse_xy(" ".join(st.args))
            self.mouse.position = (x, y)
            return
        if st.kind in ("click", "doubleclick", "hold"):
            btn_name = "left"
            pos = None
            # parse: [button] [at x,y]
            args = list(st.args)
            if args and args[0].lower() in BUTTONS:
                btn_name = args.pop(0).lower()
            if args and args[0].lower() == "at":
                args.pop(0)
                pos = _parse_xy(" ".join(args))
            btn = BUTTONS[btn_name]
            if pos is not None:
                self.mouse.position = pos
            if st.kind == "click":
                self.mouse.click(btn, 1)
            elif st.kind == "doubleclick":
                self.mouse.click(btn, 2)
            elif st.kind == "hold":
                dur = 50
                if args:
                    # last numeric could be duration
                    try:
                        dur = int(args[-1])
                        args = args[:-1]
                    except ValueError:
                        pass
                self.mouse.press(btn)
                self.stop_event.wait(dur / 1000.0)
                self.mouse.release(btn)
            return
        raise ValueError(f"unknown stmt {st.kind}")


def _parse_xy(s: str) -> tuple[int, int]:
    s = s.strip()
    # support "100,200" or "100 200"
    if "," in s:
        a, b = s.split(",", 1)
    else:
        parts = s.split()
        if len(parts) != 2:
            raise ValueError("expected x,y")
        a, b = parts
    return int(a.strip()), int(b.strip())