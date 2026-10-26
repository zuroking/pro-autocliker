from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import Profile, atomic_write_json, default_data_dir, read_json


class ProfileStore:
    def __init__(self, base: Optional[Path] = None) -> None:
        self.base = base or default_data_dir()
        self.base.mkdir(parents=True, exist_ok=True)
        self.path = self.base / "profiles.json"

    def list_names(self) -> list[str]:
        data = read_json(self.path, default=[])
        return [p.get("name", "") for p in data if isinstance(p, dict)]

    def load_all(self) -> list[Profile]:
        data = read_json(self.path, default=[])
        out: list[Profile] = []
        for item in data if isinstance(data, list) else []:
            try:
                out.append(Profile.model_validate(item))
            except Exception:
                continue
        return out

    def save_all(self, profiles: list[Profile]) -> None:
        atomic_write_json(self.path, [p.model_dump(mode="json") for p in profiles])

    def get(self, name: str) -> Optional[Profile]:
        for p in self.load_all():
            if p.name == name:
                return p
        return None

    def upsert(self, profile: Profile) -> None:
        profiles = self.load_all()
        profiles = [p for p in profiles if p.name != profile.name]
        profiles.append(profile)
        self.save_all(profiles)

    def delete(self, name: str) -> None:
        profiles = [p for p in self.load_all() if p.name != name]
        self.save_all(profiles)