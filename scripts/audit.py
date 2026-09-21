#!/usr/bin/env python3
"""Fail closed on noncanonical report files, invalid manifests, stale links or catalog."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from build_catalog import ROOT, REPORTS, CATALOG, render

AGENTS = {"market": "MARKET", "tech": "TECH", "china": "CHINA"}
FORMATS = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
REQUIRED = {"schema_version", "run_key", "agent", "date", "scheduled_time", "title", "summary", "status", "files"}
errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def verify_office(file: Path, fmt: str) -> None:
    main = "word/document.xml" if fmt == "docx" else "ppt/presentation.xml"
    try:
        with zipfile.ZipFile(file) as z:
            if z.testzip() is not None or "[Content_Types].xml" not in z.namelist() or main not in z.namelist():
                fail(f"Invalid OOXML {fmt}: {file}")
    except (OSError, zipfile.BadZipFile):
        fail(f"Invalid OOXML ZIP: {file}")


def main() -> int:
    for mandatory in ("README.md", "AGENTS.md", "index.html", "catalog.json", ".nojekyll", "scripts/build_catalog.py"):
        if not (ROOT / mandatory).is_file():
            fail(f"Missing project file: {mandatory}")
    seen: set[str] = set()
    referenced: set[Path] = set()
    manifests = sorted(REPORTS.rglob("manifest.json")) if REPORTS.exists() else []
    for manifest in manifests:
        rel = manifest.relative_to(ROOT)
        parts = rel.parts
        if len(parts) != 7 or parts[0] != "reports" or parts[-1] != "manifest.json":
            fail(f"Manifest placed outside canonical run directory: {rel}")
            continue
        _, agent, yyyy, mm, dd, run_key, _ = parts
        if agent not in AGENTS or not re.fullmatch(r"20\d\d", yyyy) or not re.fullmatch(r"\d\d", mm) or not re.fullmatch(r"\d\d", dd):
            fail(f"Invalid agent/date folder: {rel}")
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            fail(f"Unreadable manifest {rel}: {exc}")
            continue
        if set(data) != REQUIRED or data.get("schema_version") != 1:
            fail(f"Unexpected manifest schema: {rel}")
            continue
        date = f"{yyyy}-{mm}-{dd}"
        if data["agent"] != agent or data["date"] != date or data["run_key"] != run_key:
            fail(f"Manifest and folder disagree: {rel}")
        try:
            from datetime import date as Date
            Date.fromisoformat(date)
        except ValueError:
            fail(f"Impossible calendar date: {rel}")
        expected_prefix = AGENTS[agent]
        pattern = rf"{expected_prefix}-{date}-(?:\d{{4}}|MANUAL-\d{{4}})"
        if not re.fullmatch(pattern, run_key):
            fail(f"Invalid RUN_KEY for agent/date: {run_key}")
        time = data["scheduled_time"]
        if not isinstance(time, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time):
            fail(f"Invalid scheduled time: {rel}")
        elif run_key.endswith("-" + time.replace(":", "")) is False:
            fail(f"RUN_KEY/time mismatch: {rel}")
        if run_key.casefold() in seen:
            fail(f"Duplicate RUN_KEY: {run_key}")
        seen.add(run_key.casefold())
        if not isinstance(data["title"], str) or not data["title"].strip() or not isinstance(data["summary"], str) or not data["summary"].strip():
            fail(f"Missing public title/summary: {rel}")
        files = data["files"]
        if not isinstance(files, dict) or not files or set(files) - FORMATS.keys():
            fail(f"No verified attachments or unexpected format: {rel}")
            continue
        expected_status = "FULL" if set(files) == set(FORMATS) else "DEGRADED"
        if data["status"] != expected_status:
            fail(f"Invalid attachment status: {rel}")
        for fmt, info in files.items():
            if not isinstance(info, dict) or set(info) != {"path", "bytes", "sha256"}:
                fail(f"Bad file entry: {rel} / {fmt}")
                continue
            expected = (manifest.parent / f"report.{fmt}").resolve()
            path = info["path"]
            if not isinstance(path, str) or path != expected.relative_to(ROOT).as_posix():
                fail(f"Noncanonical or broken href: {rel} / {fmt}")
                continue
            referenced.add(expected)
            if not expected.is_file() or expected.is_symlink():
                fail(f"Missing attachment: {path}")
                continue
            raw = expected.read_bytes()
            if not isinstance(info["bytes"], int) or info["bytes"] != len(raw) or info["sha256"] != hashlib.sha256(raw).hexdigest():
                fail(f"Attachment bytes/hash mismatch: {path}")
            if fmt == "pdf" and (not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-2048:]):
                fail(f"Invalid PDF signature/end: {path}")
            if fmt in ("docx", "pptx"):
                verify_office(expected, fmt)
    if REPORTS.exists():
        for file in REPORTS.rglob("*"):
            if file.is_symlink():
                fail(f"Symlinks forbidden: {file.relative_to(ROOT)}")
            elif file.is_file() and file.name != "manifest.json" and file.resolve() not in referenced:
                fail(f"Orphan or noncanonical file: {file.relative_to(ROOT)}")
    try:
        if CATALOG.read_text(encoding="utf-8") != render():
            fail("Stale/incomplete catalog: run python3 scripts/build_catalog.py")
    except (OSError, ValueError, KeyError) as exc:
        fail(f"Unreadable or unbuildable catalog: {exc}")
    if errors:
        print("ARCHIVE AUDIT FAILED")
        for error in errors:
            print(" - " + error)
        return 1
    print(f"ARCHIVE AUDIT PASSED: {len(manifests)} manifests, {len(referenced)} verified attachments, global catalog in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
