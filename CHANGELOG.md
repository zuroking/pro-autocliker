# Changelog

All notable changes to this project are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Redesigned desktop UI (dark theme, cards, status colors, scrollable tabs).
- Added project-level documentation (`SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`, agent guides).

## [0.1.0] - 2026-10-26

### Added
- Initial release of pro-autocliker.
- Configurable mouse clicks (button, cursor/fixed position, interval, jitter, count, single/double/hold).
- Global hotkeys: F6 start/stop, F7 record macro, F12 emergency stop.
- Macro recording and playback.
- Profiles (save/load/delete).
- Scheduler (one-shot and daily).
- Script DSL (`click`, `move`, `wait`, `loop`, `hold`, `doubleclick`).
- Multi-clicker (up to 8 independent streams).

### Fixed
- Thread safety and scheduler races.
- Stop responsiveness and teardown ordering.
- Config validation and macro recording edge cases.