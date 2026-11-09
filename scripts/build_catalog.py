#!/usr/bin/env python3
"""Generate deterministic Pages catalog from every v1/v2 research manifest."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
CATALOG = ROOT / "catalog.json"
FORMAT_ORDER = ("md", "json", "pdf", "docx", "pptx")

def generate() -> dict:
    entries = []
    for file in sorted(REPORTS.glob("*/*/*/*/*/manifest.json")) if REPORTS.exists() else []:
        d = json.loads(file.read_text(encoding="utf-8"))
        entries.append({
            "run_key": d["run_key"], "agent": d["agent"], "date": d["date"],
            "scheduled_time": d["scheduled_time"], "title": d["title"],
            "summary": d["summary"], "status": d["status"],
            "schema_version": d["schema_version"],
            "files": {fmt: d["files"][fmt]["path"] for fmt in FORMAT_ORDER if fmt in d["files"]},
        })
    entries.sort(key=lambda d: (d["date"], d["scheduled_time"], d["run_key"]), reverse=True)
    return {"schema_version": 2, "reports": entries}

def render() -> str:
    return json.dumps(generate(), ensure_ascii=False, indent=2) + "\n"

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
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
