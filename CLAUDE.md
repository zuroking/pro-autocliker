# CLAUDE.md — pro-autocliker

Desktop auto-clicker for Windows (Python 3.12+, CustomTkinter + pynput). Open source.

## Build & Test

- Install: `pip install -e .` (or set `PYTHONPATH=src`)
- Run: `python -m autoclicker`
- Tests: `pytest`
- Types: `mypy --strict src`

## Layout

```
src/autoclicker/   # package
tests/             # pytest suite
```

## Conventions

- Python 3.12+, Pydantic v2, `mypy --strict`.
- No stubs (`pass`, `TODO`) in completed modules.
- No unhandled `except Exception`.
- English for code, identifiers, docstrings, commit messages.
- CPU-only; never assume GPU access.

## Safety

- No anti-cheat bypass or game-protection evasion.
- No secrets, keys, or private data in the repository.

## Notes

- Data dir: `%APPDATA%/pro-autocliker` (Windows) or `~/.config/pro-autocliker`.
- Global hotkeys may be unavailable in restricted environments.