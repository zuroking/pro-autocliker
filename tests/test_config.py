from __future__ import annotations

import pytest

from autoclicker.config import ClickConfig


def test_default_config() -> None:
    c = ClickConfig()
    assert c.interval_ms == 100
    assert c.count == 0


def test_jitter_too_large() -> None:
    with pytest.raises(ValueError):
        ClickConfig(interval_ms=100, interval_jitter_ms=60)


def test_jitter_ok() -> None:
    c = ClickConfig(interval_ms=100, interval_jitter_ms=40)
    assert c.interval_jitter_ms == 40


def test_interval_min() -> None:
    with pytest.raises(ValueError):
        ClickConfig(interval_ms=0)