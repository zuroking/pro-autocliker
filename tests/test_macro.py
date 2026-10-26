from __future__ import annotations

from autoclicker.config import Macro, MacroEvent
from autoclicker.macro import MacroPlayer

from conftest import FakeMouse


def test_macro_serialization() -> None:
    m = Macro(name="m", events=[MacroEvent(t_ms=0, kind="move", data={"x": 1, "y": 2})], speed=2.0)
    d = m.model_dump(mode="json")
    m2 = Macro.model_validate(d)
    assert m2.name == "m"
    assert m2.events[0].data == {"x": 1, "y": 2}


def test_macro_player_runs() -> None:
    mouse = FakeMouse()
    from pynput import keyboard as kb

    kb_controller = kb.Controller()
    m = Macro(name="m", events=[
        MacroEvent(t_ms=0, kind="move", data={"x": 5, "y": 6}),
        MacroEvent(t_ms=10, kind="click", data={"x": 7, "y": 8, "button": "Button.left"}),
    ], speed=10.0)
    player = MacroPlayer(m, mouse, kb_controller)
    player.start()
    import time
    time.sleep(1.0)
    player.stop()
    assert mouse.position == (7, 8)