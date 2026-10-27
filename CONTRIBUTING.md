# Contributing

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Running

```bash
python -m autoclicker   # with package installed
# or
$env:PYTHONPATH = "src"; python -m autoclicker
```

## Tests

```bash
pytest
mypy --strict src
```

Raw `pytest -v` output is required before declaring a change done.

## Style

- Python 3.12+, type hints, `mypy --strict`.
- Pydantic v2 for models.
- No stubs (`pass`, `TODO`) in completed modules.
- No unhandled `except Exception`.
- English for code, identifiers, docstrings, commit messages.

## Pull Requests

- Keep changes focused.
- Add or update tests for behavior changes.
- Update `CHANGELOG.md` for user-visible changes.
- Do not include secrets or private data.