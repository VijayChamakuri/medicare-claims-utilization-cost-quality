"""Command line interface: ``medicare-claims <command>``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import duckdb

from medicare_claims.config import Config, load_config


def _connect(config: Config, must_exist: bool = True) -> duckdb.DuckDBPyConnection:
    if config.warehouse != ":memory:" and must_exist and not Path(config.warehouse).exists():
        raise SystemExit(f"No warehouse at {config.warehouse}. Run `medicare-claims build` first.")
    return duckdb.connect(config.warehouse)


def _download(config: Config, args: argparse.Namespace) -> None:
    from medicare_claims.download import download

    manifest = download(config, refresh_manifest=args.refresh_manifest, force=args.force)
    print(f"Verified {len(manifest['files'])} files; manifest at {config.manifest_path}")


def _build(config: Config, args: argparse.Namespace) -> None:
    from medicare_claims.model import blocking_failures, build_warehouse

    if config.warehouse != ":memory:":
        Path(config.warehouse).parent.mkdir(parents=True, exist_ok=True)  # absent on a fresh clone
    con = build_warehouse(config, duckdb.connect(config.warehouse))
    failures = blocking_failures(con)
    passed, total = con.execute("select count(*) filter (where passed), count(*) from reconciliation_results").fetchone()  # type: ignore[misc]
    print(f"Warehouse built at {config.warehouse}: {passed} of {total} reconciliation checks passed")
    if failures:
        for name, expected, actual in failures:
            print(f"  BLOCKING {name}: expected {expected}, actual {actual}")
        raise SystemExit(1)


def _validate(config: Config, args: argparse.Namespace) -> None:
    from medicare_claims.model import blocking_failures
    from medicare_claims.validation import compare

    con = _connect(config)
    failures = blocking_failures(con)
    result = compare(con, config)
    bad = result[~result["passed"]]
    print(f"{len(result) - len(bad)} of {len(result)} independent pandas checks agree with the warehouse")
    if len(bad) or failures:
        print(bad.to_string(index=False))
        raise SystemExit(1)


def _export(config: Config, args: argparse.Namespace) -> None:
    from medicare_claims.export import write_exports

    written = write_exports(_connect(config), config)
    print(f"Wrote {len(written)} datasets to {config.exports_dir}")


def _excel(config: Config, args: argparse.Namespace) -> None:
    from medicare_claims.excel import build_workbook

    print(build_workbook(_connect(config), config))


def _reports(config: Config, args: argparse.Namespace) -> None:
    from medicare_claims.reports import write_reports

    write_reports(_connect(config), config, run_independent=not args.skip_independent)
    print(f"Wrote {config.reports_dir} (executive summary, data quality report, provider action list, headline KPIs)")


def _dashboard(config: Config, args: argparse.Namespace) -> None:
    from medicare_claims.dashboard import build_dashboard

    print(build_dashboard(_connect(config), config))


def _tableau(config: Config, args: argparse.Namespace) -> None:
    from medicare_claims.tableau import build_package

    print(build_package(_connect(config), config))


def _readme(config: Config, args: argparse.Namespace) -> None:
    from medicare_claims.reports import check_readme, write_readme

    if args.check:
        problems = check_readme(config)
        if problems:
            print("README is out of sync with reports/headline_kpis.json:\n  " + "\n  ".join(problems))
            raise SystemExit(1)
        print("README matches reports/headline_kpis.json")
    else:
        write_readme(config)
        print("README generated blocks refreshed")


def _all(config: Config, args: argparse.Namespace) -> None:
    _download(config, argparse.Namespace(refresh_manifest=False, force=False))
    _build(config, args)
    _validate(config, args)
    _export(config, args)
    _excel(config, args)
    _reports(config, argparse.Namespace(skip_independent=False))
    _tableau(config, args)
    _dashboard(config, args)
    _readme(config, argparse.Namespace(check=False))


COMMANDS: dict[str, tuple[str, Callable[[Config, argparse.Namespace], None]]] = {
    "download": ("Download official CMS and AHRQ files and record hashes", _download),
    "build": ("Load raw files and build the DuckDB warehouse with reconciliation", _build),
    "validate": ("Compare the warehouse with an independent pandas recomputation", _validate),
    "export": ("Write aggregated CSV datasets", _export),
    "excel": ("Build excel/claims_operations_review.xlsx from the marts", _excel),
    "reports": ("Write executive summary, data quality report and provider action list", _reports),
    "tableau": ("Write the Tableau data extracts and documentation", _tableau),
    "dashboard": ("Build the offline dashboard", _dashboard),
    "readme": ("Refresh or check the README generated blocks", _readme),
    "all": ("Run every stage in order", _all),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="medicare-claims", description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--profile", default=None, help="sample1 (default) or fixture")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (help_text, _) in COMMANDS.items():
        p = sub.add_parser(name, help=help_text)
        if name == "download":
            p.add_argument("--refresh-manifest", action="store_true")
            p.add_argument("--force", action="store_true")
        if name == "reports":
            p.add_argument("--skip-independent", action="store_true")
        if name == "readme":
            p.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    config = load_config(args.config, args.root, args.profile)
    COMMANDS[args.command][1](config, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
