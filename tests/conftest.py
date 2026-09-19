from __future__ import annotations

from pathlib import Path

import pytest

from medicare_claims.config import Config, load_config
from medicare_claims.model import build_warehouse

REPO = Path(__file__).resolve().parents[1]


def fixture_config() -> Config:
    """The fixture profile with the small review thresholds used in the hand derivation."""
    cfg = load_config(root=REPO, profile="fixture")
    cfg.raw["metrics"]["review"].update({"peer_min_providers": 4, "min_claims": 1, "iqr_multiplier": 1.5})
    cfg.raw["profiles"]["fixture"]["warehouse"] = ":memory:"
    return cfg


@pytest.fixture(scope="session")
def config() -> Config:
    return fixture_config()


@pytest.fixture(scope="session")
def warehouse(config: Config):
    con = build_warehouse(config)
    yield con
    con.close()
