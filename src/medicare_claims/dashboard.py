"""Build dashboard/index.html, one offline file, from the DuckDB marts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from medicare_claims.config import Config
from medicare_claims.export import datasets
from medicare_claims.quality import all_quality
from medicare_claims.validation import compare


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient="records", double_precision=10))


def build_payload(con: duckdb.DuckDBPyConnection, config: Config, independent: pd.DataFrame | None = None) -> dict[str, Any]:
    ds = datasets(con, config)
    review = config.metrics["review"]
    fac = ds["provider_review_facility"]
    fac = pd.concat([g[g["review_flag"] | (g["payment_amount"].rank(ascending=False, method="first") <= 400)] for _, g in fac.groupby(["year", "provider_type"])])
    manifest_path = config.manifest_path
    retrieved = "fixture data"
    if manifest_path and manifest_path.exists():
        files = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
        retrieved = max(f["retrieved_at"] for f in files.values())
    ind = independent if independent is not None else (compare(con, config) if config.is_fixture else _load_independent(config))
    payload: dict[str, Any] = {name: _records(frame) for name, frame in ds.items()
                               if name not in ("provider_review_facility", "provider_review_professional_top")}
    payload["provider_review_facility"] = _records(fac)
    payload["independent"] = _records(ind)
    payload["data_quality"] = json.loads(json.dumps(all_quality(con), default=float))
    payload["meta"] = {
        "source_name": config.raw["source"]["name"], "overview_url": config.raw["source"]["overview_url"],
        "codebook_url": config.raw["source"]["codebook_url"], "retrieved": retrieved,
        "ccs_name": config.raw["reference"]["ccs"]["name"], "peer_min": int(review["peer_min_providers"]),
        "min_claims": int(review["min_claims"]),
    }
    return payload


def _load_independent(config: Config) -> pd.DataFrame:
    path = config.reports_dir / "independent_reconciliation.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["check", "passed"])


def _inline(text: str) -> str:
    return text.replace("</", "<\\/")


def build_dashboard(con: duckdb.DuckDBPyConnection, config: Config, output: Path | None = None) -> Path:
    folder = config.root / "dashboard"
    template = (folder / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(build_payload(con, config), separators=(",", ":"), allow_nan=False)
    html = (template.replace("/*STYLE*/", (folder / "style.css").read_text(encoding="utf-8"))
            .replace("/*APP*/", _inline((folder / "app.js").read_text(encoding="utf-8")))
            .replace("/*DATA*/", _inline(payload)))
    target = output or config.artifacts_root / "dashboard" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target
