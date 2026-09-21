#!/usr/bin/env python3
"""Build the deterministic GitHub Pages catalog from canonical report manifests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
CATALOG = ROOT / "catalog.json"


def generate() -> dict:
    entries = []
    for file in sorted(REPORTS.glob("*/*/*/*/*/manifest.json")) if REPORTS.exists() else []:
        data = json.loads(file.read_text(encoding="utf-8"))
        entries.append({
            "run_key": data["run_key"],
            "agent": data["agent"],
            "date": data["date"],
            "scheduled_time": data["scheduled_time"],
            "title": data["title"],
            "summary": data["summary"],
            "status": data["status"],
            "files": {fmt: data["files"][fmt]["path"] for fmt in ("pdf", "docx", "pptx") if fmt in data["files"]},
        })
    entries.sort(key=lambda x: (x["date"], x["scheduled_time"], x["run_key"]), reverse=True)
    return {"schema_version": 1, "reports": entries}


def render() -> str:
    return json.dumps(generate(), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if committed catalog differs from manifests")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not CATALOG.exists() or CATALOG.read_text(encoding="utf-8") != expected:
            print("ERROR: catalog.json is stale; run python3 scripts/build_catalog.py")
            return 1
        print("OK: catalog.json matches all manifests")
        return 0
    CATALOG.write_text(expected, encoding="utf-8")
    print(f"Updated catalog.json: {len(generate()['reports'])} reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
