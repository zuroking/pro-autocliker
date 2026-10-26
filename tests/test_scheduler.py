from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from autoclicker.config import Schedule
from autoclicker.scheduler import Scheduler


def test_scheduler_due() -> None:
    triggered: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sched = Scheduler(on_trigger=lambda s: triggered.append(s.name), base_dir=base)
        past = datetime.now() - timedelta(seconds=5)
        sched.add(Schedule(name="s1", profile_name="p", run_at=past, repeat="once"))
        sched.start()
        import time
        time.sleep(2.0)
        sched.stop()
        assert "s1" in triggered
        # one-shot disabled
        remaining = sched.load()
        assert all(not s.enabled for s in remaining if s.name == "s1")