# ARCHITECTURE.md — pro-autocliker

**as of 2026-10-26 · v1.0 draft · CPU-only desktop app (Windows, Python 3.12+)**

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
| Concurrency | `threading` + `queue` | Simple, sufficient for click streams |
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
  hotkeys.py            # GlobalHotkeyManager (pynput keyboard listener)
  macro.py              # MacroRecorder / MacroPlayer
  scheduler.py          # Scheduler (time-based triggers)
  scripts.py            # tiny DSL interpreter for click scripts
  profiles.py           # ProfileStore (load/save/list)
  ui/
    app.py              # CTk root + wiring
    main_window.py      # main control panel
    profile_panel.py
    macro_panel.py
    scheduler_panel.py
    script_editor.py
    multi_panel.py
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

`MouseController` is a `Protocol` (move, click, press, release, position) so the
engine is testable with a fake. pynput's `Controller` satisfies it.

`Profile` = name + ClickConfig + hotkey bindings.
`Macro` = list of events (move/click/scroll/key) with timestamps (relative).
`Schedule` = cron-like or one-shot datetime + profile name + repeat.
`Script` = list of DSL statements.

## 5. Engine contract

`ClickEngine(config, on_status)`:
- `start()` spawns a daemon thread; `stop()` sets an Event.
- Thread loop: for each click iteration, if count reached -> stop.
  - fixed mode: `mouse.position = (x,y)` then click; restore cursor if configured.
  - jitter: `stop_event.wait(interval + uniform(-jitter, jitter))` (wakes on stop).
  - hold: press, wait(hold_duration), release.
  - double: two clicks with ~50 ms gap.
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
Configurable per profile.

## 7. Macro recording

`MacroRecorder` captures `mouse` + `keyboard` events with timestamps via
pynput listeners. Stored as list of `{t_ms, kind, ...}`. Player replays with
original timing scaled by speed factor. Recording stops on hotkey.

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
Files: `profiles.json`, `macros.json`, `schedules.json`, `scripts/*.txt`, `settings.json`.

## 12. UI

CustomTkinter. Main window: config form + start/stop + status + hotkey hints.
Tabs: Profiles, Macros, Scheduler, Scripts, Multi. Emergency stop always visible (red, large).

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

Semantic. v0.1 = engine + basic UI. v0.2 = hotkeys + profiles. v0.3 = macros.
v0.4 = scheduler + scripts. v0.5 = multi-clicker. v1.0 = polish + packaging.