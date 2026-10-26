from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from .config import Schedule, atomic_write_json, default_data_dir, read_json


class Scheduler:
    """Polls every second for due schedules and triggers a callback."""

    def __init__(
        self,
        on_trigger: Callable[[Schedule], None],
        base_dir: Optional[Path] = None,
    ) -> None:
        self.on_trigger = on_trigger
        self.base_dir = base_dir
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        root = self.base_dir if self.base_dir is not None else default_data_dir()
        root.mkdir(parents=True, exist_ok=True)
        return root / "schedules.json"

    def load(self) -> list[Schedule]:
        data = read_json(self.path, default=[])
        out: list[Schedule] = []
        for item in data if isinstance(data, list) else []:
            try:
                out.append(Schedule.model_validate(item))
            except Exception:
                continue
        return out

    def save(self, schedules: list[Schedule]) -> None:
        atomic_write_json(self.path, [s.model_dump(mode="json") for s in schedules])

    def add(self, schedule: Schedule) -> None:
        schedules = self.load()
        schedules.append(schedule)
        self.save(schedules)

    def remove(self, name: str) -> None:
        schedules = [s for s in self.load() if s.name != name]
        self.save(schedules)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            now = datetime.now()
            due: list[Schedule] = []
            with self._lock:
                schedules = self.load()
                changed = False
                for s in schedules:
                    if not s.enabled:
                        continue
                    if s.run_at <= now:
                        due.append(s)
                        if s.repeat == "daily":
                            s.run_at = s.run_at + timedelta(days=1)
                            while s.run_at <= now:
                                s.run_at = s.run_at + timedelta(days=1)
                        else:
                            s.enabled = False
                        changed = True
                if changed:
                    self.save(schedules)
            for s in due:
                try:
                    self.on_trigger(s)
                except Exception:
                    pass
            self._stop.wait(1.0)