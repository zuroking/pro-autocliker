from __future__ import annotations

import time

from autoclicker.scripts import parse, ScriptError, ScriptRunner

from conftest import FakeMouse


def test_parse_simple() -> None:
    src = "click left at 10,20\nwait 100\nmove 30 40\n"
    stmts = parse(src)
    assert len(stmts) == 3
    assert stmts[0].kind == "click"
    assert stmts[2].kind == "move"


def test_parse_loop() -> None:
    src = "loop 3 {\n  click left\n  wait 10\n}\n"
    stmts = parse(src)
    assert len(stmts) == 1
    assert stmts[0].kind == "loop"
    assert len(stmts[0].body) == 2


def test_parse_unknown() -> None:
    with __import__("pytest").raises(ScriptError):
        parse("frobnicate 1\n")


def test_runner_executes() -> None:
    mouse = FakeMouse()
    runner = ScriptRunner(mouse)
    src = "move 5,6\nclick right at 7,8\ndoubleclick left\nwait 10\n"
    runner.run(src)
    # allow thread to finish
    time.sleep(0.5)
    assert mouse.position == (7, 8)
    # at least one click happened
    assert len(mouse.clicks) >= 1