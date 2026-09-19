"""Manifest and integrity behavior, with local files only (no network)."""

import copy
import hashlib
import json
import zipfile

import pytest

from medicare_claims.config import Config, load_config
from medicare_claims.download import DataIntegrityError, download
from tests.conftest import REPO


def _config(tmp_path) -> Config:
    raw = copy.deepcopy(load_config(root=REPO).raw)
    profile = raw["profiles"]["sample1"]
    profile.update({"raw_dir": "raw", "manifest": "manifest.json"})
    # Keep one small archive per kind so every entry can be satisfied locally.
    profile["files"] = {
        "beneficiary": [{"year": 2008, "name": "bene.zip", "csv": "b.csv", "url": "http://invalid.example/bene.zip"}],
        "inpatient": [{"name": "ip.zip", "csv": "i.csv", "url": "http://invalid.example/ip.zip"}],
        "outpatient": [{"name": "op.zip", "csv": "o.csv", "url": "http://invalid.example/op.zip"}],
        "carrier": [{"name": "ca.zip", "csv": "c.csv", "url": "http://invalid.example/ca.zip"}],
    }
    profile["documents"] = [{"name": "codebook.pdf", "url": "http://invalid.example/codebook.pdf"}]
    (tmp_path / "raw").mkdir()
    (tmp_path / "reference").mkdir()
    (tmp_path / "reference" / "ccs_icd9_dx_2015.csv").write_text("icd9_code,ccs_category,ccs_category_name\n")
    return Config(raw, tmp_path, "sample1")


def _populate(config: Config, marker: str = "a") -> None:
    for name in ("bene", "ip", "op", "ca"):
        with zipfile.ZipFile(config.raw_dir / f"{name}.zip", "w") as zf:
            zf.writestr("data.csv", f"x,{marker}\n1,2\n")
    (config.raw_dir / "codebook.pdf").write_bytes(b"%PDF-1.4 " + marker.encode())
    ccs = config.raw_dir / "ccs_single_level_2015.zip"
    with zipfile.ZipFile(ccs, "w") as zf:
        zf.writestr("dx.csv", "code\n1\n")
    config.raw["reference"]["ccs"]["zip_sha256"] = hashlib.sha256(ccs.read_bytes()).hexdigest()


def test_manifest_records_url_date_size_and_hash(tmp_path) -> None:
    config = _config(tmp_path)
    _populate(config)
    manifest = download(config)
    entry = manifest["files"]["ip.zip"]
    assert entry["source_url"] == "http://invalid.example/ip.zip" and len(entry["sha256"]) == 64
    assert entry["retrieved_at"] and entry["bytes"] == (config.raw_dir / "ip.zip").stat().st_size
    assert entry["members"] == ["data.csv"]
    assert manifest["reference"]["ccs_compact_sha256"] and manifest["source"]["codebook_url"]
    assert json.loads(config.manifest_path.read_text())["files"].keys() == manifest["files"].keys()


def test_a_changed_source_file_stops_the_run_until_refreshed(tmp_path) -> None:
    config = _config(tmp_path)
    _populate(config, "a")
    first = download(config)
    _populate(config, "b")  # the source was revised
    config.raw["reference"]["ccs"]["zip_sha256"] = hashlib.sha256((config.raw_dir / "ccs_single_level_2015.zip").read_bytes()).hexdigest()
    with pytest.raises(DataIntegrityError, match="does not match the manifest"):
        download(config)
    refreshed = download(config, refresh_manifest=True)
    assert refreshed["files"]["ip.zip"]["sha256"] != first["files"]["ip.zip"]["sha256"]


def test_the_pinned_reference_hash_is_enforced(tmp_path) -> None:
    config = _config(tmp_path)
    _populate(config)
    config.raw["reference"]["ccs"]["zip_sha256"] = "0" * 64
    with pytest.raises(DataIntegrityError, match="pinned"):
        download(config)


def test_a_corrupt_archive_or_fake_pdf_is_rejected(tmp_path) -> None:
    config = _config(tmp_path)
    _populate(config)
    (config.raw_dir / "codebook.pdf").write_bytes(b"<html>not a pdf</html>")
    with pytest.raises(DataIntegrityError, match="not a PDF"):
        download(config)
    _populate(config)
    (config.raw_dir / "ip.zip").write_bytes(b"this is not a zip")
    with pytest.raises(zipfile.BadZipFile):
        download(config)


def test_the_fixture_profile_needs_no_download(config) -> None:
    assert download(config) == {"schema_version": 1, "files": {}}
