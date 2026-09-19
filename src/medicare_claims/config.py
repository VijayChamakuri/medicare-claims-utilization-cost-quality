"""Typed access to config/project.yml and the active data profile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path("config/project.yml")


@dataclass(frozen=True)
class Config:
    raw: dict[str, Any]
    root: Path
    profile_name: str

    @property
    def profile(self) -> dict[str, Any]:
        return dict(self.raw["profiles"][self.profile_name])

    @property
    def study_start(self) -> date:
        return date.fromisoformat(str(self.raw["study"]["start"]))

    @property
    def study_end(self) -> date:
        return date.fromisoformat(str(self.raw["study"]["end"]))

    @property
    def metrics(self) -> dict[str, Any]:
        return dict(self.raw["metrics"])

    @property
    def raw_dir(self) -> Path:
        return self.root / str(self.profile["raw_dir"])

    @property
    def interim_dir(self) -> Path | None:
        value = self.profile.get("interim_dir")
        return self.root / str(value) if value else None

    @property
    def manifest_path(self) -> Path | None:
        value = self.profile.get("manifest")
        return self.root / str(value) if value else None

    @property
    def warehouse(self) -> str:
        value = str(self.profile["warehouse"])
        return value if value == ":memory:" else str(self.root / value)

    @property
    def sql_dir(self) -> Path:
        return self.root / "sql"

    @property
    def artifacts_root(self) -> Path:
        """Where generated artifacts go. Fixture runs are kept apart so they never overwrite real-sample outputs."""
        return self.root / "build" / "fixture" if self.is_fixture else self.root

    @property
    def exports_dir(self) -> Path:
        return self.artifacts_root / "exports"

    @property
    def reports_dir(self) -> Path:
        return self.artifacts_root / "reports"

    @property
    def readme_path(self) -> Path:
        return self.artifacts_root / "README.md"

    @property
    def is_fixture(self) -> bool:
        return self.profile_name == "fixture"

    def files(self, kind: str) -> list[dict[str, Any]]:
        return [dict(item) for item in self.profile["files"][kind]]

    def csv_path(self, item: dict[str, Any]) -> Path:
        """Location of the CSV for a file entry (extracted copy, or the raw dir for fixtures)."""
        base = self.interim_dir or self.raw_dir
        return base / str(item["csv"])


def load_config(path: Path | str | None = None, root: Path | str | None = None,
                profile: str | None = None) -> Config:
    base = Path(root) if root else Path.cwd()
    config_path = Path(path) if path else base / DEFAULT_CONFIG
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    name = profile or str(raw["profile"])
    if name not in raw["profiles"]:
        raise KeyError(f"Unknown profile {name!r}; choose from {sorted(raw['profiles'])}")
    return Config(raw, base, name)
