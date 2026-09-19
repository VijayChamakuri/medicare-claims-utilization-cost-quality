"""Check that every official source URL in config/project.yml still responds. Run by the scheduled CI job."""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import yaml

RAW = yaml.safe_load(Path("config/project.yml").read_text(encoding="utf-8"))


def urls() -> list[str]:
    found = [RAW["source"][k] for k in ("overview_url", "collection_url", "codebook_url", "faq_url")]
    found.append(RAW["reference"]["ccs"]["landing_url"])
    profile = RAW["profiles"]["sample1"]
    for kind in ("beneficiary", "inpatient", "outpatient", "carrier"):
        found += [item["url"] for item in profile["files"][kind]]
    found += [doc["url"] for doc in profile["documents"]]
    return found


def check(url: str) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": "link-check"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status in (200, 206), str(response.status)
    except Exception as error:  # noqa: BLE001 - report any failure as a broken link
        return False, str(error)


if __name__ == "__main__":
    failed = 0
    for url in urls():
        ok, detail = check(url)
        failed += not ok
        print(("ok    " if ok else "FAIL  ") + detail + "  " + url)
    sys.exit(1 if failed else 0)
