# ARCHITECTURE.md — pro-autocliker

**as of 2026-10-26 · v0.1.0 · CPU-only desktop app (Windows, Python 3.12+)**

## 1. Goal

A desktop auto-clicker that competes with OP Auto Clicker: configurable
mouse clicks (button, position mode, interval, count, hold/double-click),
global hotkeys, macro recording/playback, scheduled runs, profiles, a small
script DSL, and multi-clicker (independent click streams). Local-only, no
network, no telemetry.

## 2. Stack (locked)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12+ (verified 3.14.6) | Zuro's primary stack |
| GUI | `customtkinter` 6.x | Modern look, pure Python, no web runtime |
| Input control | `pynput` 1.8.2 | Cross-platform mouse/keyboard, global hotkeys |
| Config/validation | `pydantic` v2 | Typed, validated profiles |
| Persistence | JSON files under `%APPDATA%/pro-autocliker` | Human-readable, diffable |
| Concurrency | `threading` | Simple, sufficient for click streams |
| Packaging | `pyinstaller` (optional, later) | Single exe |

No `PyAutoGUI` for the click path (pynput is lower-level and more reliable
for hold/repeat). Pillow only for screenshot-based position picking (optional).

## 3. Module layout (src layout)

```
src/autoclicker/
  __init__.py
  __main__.py           # entrypoint
  config.py             # Pydantic models: ClickConfig, Profile, Macro, Schedule, Script
  engine.py             # ClickEngine (one stream)
  multiclicker.py       # MultiClicker orchestrates N engines
  hotkeys.py            # HotkeyManager (pynput keyboard listener)
  macro.py              # MacroRecorder / MacroPlayer
  scheduler.py          # Scheduler (time-based triggers)
  scripts.py            # tiny DSL interpreter for click scripts
  profiles.py           # ProfileStore (load/save/list)
  ui/
    app.py              # CTk root + wiring
    main_window.py      # single monolithic window with tabview
tests/
  test_config.py
  test_engine.py
  test_macro.py
  test_scripts.py
  test_scheduler.py
```

## 4. Core data model (locked)

```python
class ClickConfig(BaseModel):
    button: Literal["left","right","middle"] = "left"
    mode: Literal["cursor","fixed"] = "cursor"     # click at cursor or fixed x,y
    x: int = 0
    y: int = 0
    restore_cursor: bool = False                   # return cursor after fixed click
    interval_ms: int = 100                        # >= 1
    interval_jitter_ms: int = 0                   # random +/- for "human" mode
    count: int = 0                               # 0 = infinite
    click_type: Literal["single","double","hold"] = "single"
    hold_duration_ms: int = 50
    repeat_until_stopped: bool = True

    @field_validator("interval_jitter_ms")
    def _jitter_le_interval(cls, v, info): ...    # v <= info.data["interval_ms"] // 2
```

`MouseController` is a `Protocol` (position, click, press, release) so the
engine is testable with a fake. pynput's `Controller` satisfies it.

`Profile` = name + ClickConfig + hotkey bindings.
`Macro` = list of events (move/press/release/scroll/key) with timestamps (relative).
`Schedule` = one-shot or daily datetime + profile name + repeat (no cron).
`Script` = list of DSL statements.

## 5. Engine contract

`ClickEngine(config, on_status)`:
- `start()` spawns a daemon thread; `stop()` sets an Event.
- Thread loop: for each click iteration, if count reached -> stop.
  - fixed mode: `mouse.position = (x,y)` then click; restore cursor if configured.
  - jitter: `stop_event.wait(interval + uniform(-jitter, jitter))` (wakes on stop).
  - hold: press, wait(hold_duration), release.
  - double: `mouse.click(btn, 2)` (pynput's double-click).
- Never blocks the UI thread. `on_status(str)` is called from worker thread;
  UI wraps it in `root.after(0, ...)`.
- Use `stop_event.wait(timeout)` instead of `time.sleep` so stop is responsive.
- Multi-clicker: each engine owns its own Event; shared global MouseController
  guarded by a lock for position writes (best-effort interleaving accepted).
- Thread-safe stop via `threading.Event`.

## 6. Hotkeys

Global hotkeys via `pynput.keyboard.GlobalHotKeys`. Default:
- F6 = start/stop toggle
- F7 = record macro toggle
- F12 = emergency stop (kills all engines + macros). Esc avoided: it would
  hijack text input globally. Configurable, with on-screen warning.
Configurable per profile (data model present; no UI in v0.1).

## 7. Macro recording

`MacroRecorder` captures mouse events (keyboard capture is opt-in via
`record_keyboard`, off by default for privacy). Player replays mouse events
with original timing scaled by speed factor; keyboard events are not replayed
in v0.1 (safety). Recording stops on hotkey.

## 8. Scheduler

Background thread checks every 1s for due schedules; triggers profile start.
One-shot and repeating (daily). Persisted to JSON.

## 9. Script DSL

Minimal line-based DSL:
```
click left at 100,200
wait 500
move 300,400
doubleclick right
hold left 200
loop 5 { ... }
```
Parser -> AST -> interpreter calling engine primitives. Errors reported with line numbers.

## 10. Multi-clicker

`MultiClicker` holds list of `ClickEngine` instances, each with own config
and thread. Start/stop all or individually. Max N (default 8) to avoid
thread explosion.

## 11. Persistence

Base dir: `%APPDATA%/pro-autocliker/` (Windows) or `~/.config/pro-autocliker`.
Files: `profiles.json`, `macros.json`, `schedules.json`. (No scripts/*.txt or settings.json in v0.1; no scripts/ dir created.)

## 12. UI

CustomTkinter. Main window: config form + start/stop + status + hotkey hints.
Tabs: Clicker, Profiles, Macros, Scheduler, Scripts, Multi. Emergency stop
button lives in the Clicker tab (not globally visible). Hotkeys are not
configurable from the UI in v0.1 (defaults F6/F7/F12).

## 13. Testing strategy

- Unit tests for config validation, script parser, macro serialization, scheduler due-logic.
- Engine tested with a fake mouse controller (injected) to avoid real input in CI.
- No real mouse movement in tests.

## 14. Deliberate Deviations

- DD-1: No `PyAutoGUI`; pynput only. Reason: hold/repeat reliability.
- DD-2: Script DSL is line-based, not full language. Reason: scope.
- DD-3: Scheduler uses polling (1s) not OS timers. Reason: simplicity, portability.
- DD-4: Max 8 concurrent click streams. Reason: thread/CPU safety.

## 15. Out of scope (v1)

- Cloud sync, accounts, telemetry.
- Image recognition / pixel-based clicking.
- Game-specific anti-cheat bypass (explicitly not supported).

## 16. Versioning

Semantic. v0.1.0 = engine + UI + hotkeys + profiles + macros + scheduler +
scripts + multi-clicker (two commits, 2026-10-26). No remote yet.