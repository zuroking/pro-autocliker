from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator


class MouseController(Protocol):
    """Minimal mouse interface used by the engine (pynput Controller satisfies it)."""

    @property
    def position(self) -> tuple[int, int]: ...

    @position.setter
    def position(self, value: tuple[int, int]) -> None: ...

    def click(self, button: Any, count: int = 1) -> None: ...

    def press(self, button: Any) -> None: ...

    def release(self, button: Any) -> None: ...


ButtonName = Literal["left", "right", "middle"]
ModeName = Literal["cursor", "fixed"]
ClickTypeName = Literal["single", "double", "hold"]


class ClickConfig(BaseModel):
    button: ButtonName = "left"
    mode: ModeName = "cursor"
    x: int = 0
    y: int = 0
    restore_cursor: bool = False
    interval_ms: int = Field(default=100, ge=1)
    interval_jitter_ms: int = Field(default=0, ge=0)
    count: int = Field(default=0, ge=0)  # 0 = infinite
    click_type: ClickTypeName = "single"
    hold_duration_ms: int = Field(default=50, ge=1)
    repeat_until_stopped: bool = True

    @field_validator("interval_jitter_ms")
    @classmethod
    def _jitter_le_interval(cls, v: int, info: Any) -> int:
        interval = info.data.get("interval_ms", 100)
        if v > interval // 2:
            raise ValueError("interval_jitter_ms must be <= interval_ms // 2")
        return v

    @model_validator(mode="after")
    def _fixed_needs_coords(self) -> "ClickConfig":
        if self.mode == "fixed" and (self.x < 0 or self.y < 0):
            raise ValueError("fixed mode requires non-negative x,y")
        return self


class HotkeyBindings(BaseModel):
    start_stop: str = "f6"
    record_macro: str = "f7"
    emergency_stop: str = "f12"


class Profile(BaseModel):
    name: str = Field(min_length=1)
    config: ClickConfig = ClickConfig()
    hotkeys: HotkeyBindings = HotkeyBindings()


class MacroEvent(BaseModel):
    t_ms: int = Field(ge=0)
    kind: Literal["move", "click", "press", "release", "scroll", "key"]
    # payload varies by kind; kept as dict for flexibility
    data: dict[str, Any] = Field(default_factory=dict)


class Macro(BaseModel):
    name: str = Field(min_length=1)
    events: list[MacroEvent] = Field(default_factory=list)
    speed: float = Field(default=1.0, gt=0.0, le=10.0)
    record_keyboard: bool = False


class Schedule(BaseModel):
    name: str = Field(min_length=1)
    profile_name: str
    run_at: datetime  # next run time
    repeat: Literal["once", "daily"] = "once"
    enabled: bool = True


class ScriptLine(BaseModel):
    raw: str
    lineno: int


def default_data_dir() -> Path:
    import os

    if os.name == "nt":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    else:
        root = Path.home() / ".config"
    return root / "pro-autocliker"


def ensure_data_dir() -> Path:
    d = default_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeError):
        return default