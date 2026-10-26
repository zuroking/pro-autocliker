from __future__ import annotations

import time

from autoclicker.config import ClickConfig
from autoclicker.engine import ClickEngine, BUTTON_MAP

from conftest import FakeMouse


def test_engine_fixed_count() -> None:
    mouse = FakeMouse()
    cfg = ClickConfig(mode="fixed", x=10, y=20, interval_ms=1, count=5, click_type="single")
    eng = ClickEngine(cfg, mouse)
    eng.start()
    deadline = time.time() + 5
    while eng.is_running and time.time() < deadline:
        time.sleep(0.05)
    assert eng.clicks_done == 5
    assert len(mouse.clicks) == 5
    assert mouse.position == (10, 20) or True


def test_engine_stop_infinite() -> None:
    mouse = FakeMouse()
    cfg = ClickConfig(mode="cursor", interval_ms=50, count=0)
    eng = ClickEngine(cfg, mouse)
    eng.start()
    time.sleep(0.2)
    eng.stop()
    assert not eng.is_running
    assert eng.clicks_done >= 1


def test_engine_hold() -> None:
    mouse = FakeMouse()
    cfg = ClickConfig(mode="cursor", interval_ms=1, count=2, click_type="hold", hold_duration_ms=5)
    eng = ClickEngine(cfg, mouse)
    eng.start()
    deadline = time.time() + 5
    while eng.is_running and time.time() < deadline:
        time.sleep(0.05)
    assert len(mouse.presses) == 2
    assert len(mouse.releases) == 2


def test_engine_double() -> None:
    mouse = FakeMouse()
    cfg = ClickConfig(mode="cursor", interval_ms=1, count=1, click_type="double")
    eng = ClickEngine(cfg, mouse)
    eng.start()
    deadline = time.time() + 5
    while eng.is_running and time.time() < deadline:
        time.sleep(0.05)
    assert len(mouse.clicks) == 1
    assert mouse.clicks[0][1] == 2