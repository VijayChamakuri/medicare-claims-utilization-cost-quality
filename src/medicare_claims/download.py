"""Download official CMS and AHRQ files, verify integrity, and record provenance.

The manifest records source URL, retrieval date, byte size and SHA-256 for every file, plus the
codebook and FAQ that define the data. A hash that no longer matches the committed manifest stops
the run unless ``--refresh-manifest`` is given.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from medicare_claims.config import Config


class DataIntegrityError(RuntimeError):
    """A downloaded file is empty, malformed or does not match the recorded manifest."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _fetch(url: str, target: Path, attempts: int = 3) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "medicare-claims-analytics/1.0"})
    for attempt in range(1, attempts + 1):
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(target.suffix + ".part")
            with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as out:
                while chunk := response.read(1 << 20):
                    out.write(chunk)
            if partial.stat().st_size == 0:
                raise DataIntegrityError(f"Empty download from {url}")
            partial.replace(target)
            return
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == attempts:
                raise DataIntegrityError(f"Could not download {url}: {error}") from error
            time.sleep(3 * attempt)


def _entries(config: Config) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for kind in ("beneficiary", "inpatient", "outpatient", "carrier"):
        for item in config.files(kind):
            items.append({"kind": kind, "name": item["name"], "url": item["url"], "csv": item["csv"]})
    for doc in config.profile.get("documents", []):
        items.append({"kind": "document", "name": doc["name"], "url": doc["url"]})
    ccs = config.raw["reference"]["ccs"]
    items.append({"kind": "reference", "name": "ccs_single_level_2015.zip", "url": ccs["zip_url"],
                  "expected_sha256": ccs["zip_sha256"]})
    return items


def load_manifest(config: Config) -> dict[str, Any]:
    path = config.manifest_path
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": 1, "files": {}}


def download(config: Config, refresh_manifest: bool = False, force: bool = False) -> dict[str, Any]:
    if config.manifest_path is None:
        return {"schema_version": 1, "files": {}}  # fixture profile: nothing to fetch
    previous = load_manifest(config)
    files: dict[str, Any] = {}
    today = datetime.now(UTC).date().isoformat()
    for entry in _entries(config):
        path = config.raw_dir / entry["name"]
        if force or not path.exists():
            _fetch(entry["url"], path)
        digest = sha256_file(path)
        if "expected_sha256" in entry and digest != entry["expected_sha256"]:
            raise DataIntegrityError(f"{entry['name']}: SHA-256 {digest[:12]} differs from the pinned "
                                     f"{entry['expected_sha256'][:12]} in config/project.yml")
        recorded = previous["files"].get(entry["name"])
        if recorded and recorded["sha256"] != digest and not refresh_manifest:
            raise DataIntegrityError(
                f"{entry['name']}: SHA-256 {digest[:12]} does not match the manifest "
                f"{recorded['sha256'][:12]}. The source may have been revised. Rerun with "
                "--refresh-manifest to accept it after review.")
        record: dict[str, Any] = {
            "kind": entry["kind"],
            "source_url": entry["url"],
            "retrieved_at": recorded["retrieved_at"] if recorded and recorded["sha256"] == digest else today,
            "bytes": path.stat().st_size,
            "sha256": digest,
        }
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as zf:
                bad = zf.testzip()
                if bad:
                    raise DataIntegrityError(f"{entry['name']} has a corrupt member: {bad}")
                record["members"] = zf.namelist()
        elif path.suffix == ".pdf" and path.read_bytes()[:4] != b"%PDF":
            raise DataIntegrityError(f"{entry['name']} is not a PDF")
        files[entry["name"]] = record
    compact = config.root / config.raw["reference"]["ccs"]["compact_file"]
    manifest = {
        "schema_version": 1,
        "source": {k: config.raw["source"][k] for k in ("name", "overview_url", "collection_url",
                                                        "codebook_url", "faq_url")},
        "documentation": {"codebook": "de-10-codebook.pdf", "faq": "de-10-faq.pdf",
                          "note": "Hashes of the retrieved PDFs identify the documentation version."},
        "reference": {"ccs_compact_file": config.raw["reference"]["ccs"]["compact_file"],
                      "ccs_compact_sha256": sha256_file(compact),
                      "ccs_source": config.raw["reference"]["ccs"]["landing_url"],
                      "note": config.raw["reference"]["ccs"]["icd9_era_note"]},
        "files": files,
    }
    config.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    config.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
