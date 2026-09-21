#!/usr/bin/env python3
"""Publish one verified report ZIP using the local user's configured Git credentials.

Usage: python3 scripts/publish_bundle.py tech-report-bundle.zip
This does not send email and never force-pushes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

DEFAULT_REPO = "https://github.com/1998x-stack/cron-news.git"
FORMATS = {"pdf", "docx", "pptx"}
REQUIRED = {"schema_version", "run_key", "agent", "date", "scheduled_time", "title", "summary", "status", "files"}


def run(args: list[str], *, cwd: Path | None = None, capture: bool = False):
    return subprocess.run(args, cwd=cwd, check=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def load_bundle(bundle: Path) -> tuple[dict, dict[str, bytes]]:
    with zipfile.ZipFile(bundle) as archive:
        entries = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    manifests = [n for n in entries if n.endswith("/manifest.json")]
    if len(manifests) != 1:
        raise ValueError("Expected precisely one canonical manifest")
    manifest_name = manifests[0]
    manifest = json.loads(entries[manifest_name])
    if set(manifest) != REQUIRED or manifest["schema_version"] != 1:
        raise ValueError("Incorrect manifest schema")
    agent, date, key = manifest["agent"], manifest["date"], manifest["run_key"]
    if agent not in {"market", "tech", "china"} or not re.fullmatch(
        rf"{agent.upper()}-{re.escape(date)}-(?:\d{{4}}|MANUAL-\d{{4}})", key
    ) or not re.fullmatch(r"20\d\d-\d\d-\d\d", date):
        raise ValueError("Invalid agent/date/RUN_KEY")
    if not re.fullmatch(r"\d\d:\d\d", manifest["scheduled_time"]) or not key.endswith(
        "-" + manifest["scheduled_time"].replace(":", "")
    ):
        raise ValueError("RUN_KEY and scheduled time mismatch")
    if any(re.search(r"[\w.+-]+@[\w.-]+", manifest[k]) for k in ("title", "summary")):
        raise ValueError("Public title/summary includes an email address")
    y, m, d = date.split("-")
    prefix = f"reports/{agent}/{y}/{m}/{d}/{key}/"
    if manifest_name != prefix + "manifest.json":
        raise ValueError("Manifest is not in the canonical destination")
    files = manifest["files"]
    if not isinstance(files, dict) or not files or set(files) - FORMATS:
        raise ValueError("Bundle contains no valid formats")
    if manifest["status"] != ("FULL" if set(files) == FORMATS else "DEGRADED"):
        raise ValueError("Attachment availability status does not match manifest")
    expected = {manifest_name} | {prefix + "report." + fmt for fmt in files}
    if set(entries) != expected:
        raise ValueError(f"Unexpected/missing bundle paths: {sorted(set(entries) ^ expected)}")
    for fmt, meta in files.items():
        name = prefix + "report." + fmt
        raw = entries[name]
        if set(meta) != {"path", "bytes", "sha256"} or meta["path"] != name:
            raise ValueError("Noncanonical file metadata: " + fmt)
        if meta["bytes"] != len(raw) or meta["sha256"] != hashlib.sha256(raw).hexdigest():
            raise ValueError("Size or SHA-256 mismatch: " + name)
        if fmt == "pdf" and (not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-2048:]):
            raise ValueError("Invalid PDF: " + name)
        if fmt in {"docx", "pptx"}:
            part = "word/document.xml" if fmt == "docx" else "ppt/presentation.xml"
            with zipfile.ZipFile(io.BytesIO(raw)) as office:
                if office.testzip() or "[Content_Types].xml" not in office.namelist() or part not in office.namelist():
                    raise ValueError("Invalid Office package: " + name)
    return manifest, entries


def publish(manifest: dict, entries: dict[str, bytes], repo: str, branch: str, attempts: int):
    run_key = manifest["run_key"]
    for attempt in range(1, attempts + 1):
        with tempfile.TemporaryDirectory(prefix="archive-bundle-") as tmp:
            checkout = Path(tmp) / "checkout"
            run(["git", "clone", "--quiet", "--depth", "1", "--branch", branch, repo, str(checkout)])
            for name, raw in entries.items():
                target = checkout / name
                if target.exists() and target.read_bytes() != raw:
                    raise ValueError("Refusing to overwrite an existing RUN_KEY: " + name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            run([sys.executable, "scripts/build_catalog.py"], cwd=checkout)
            run([sys.executable, "scripts/build_catalog.py", "--check"], cwd=checkout)
            run([sys.executable, "scripts/audit.py"], cwd=checkout)
            run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=checkout)
            run(["git", "add", "--", "catalog.json", *sorted(entries)], cwd=checkout)
            staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=checkout)
            if staged.returncode == 0:
                print(f"ALREADY_ARCHIVED: {run_key}; no new email or commit")
            elif staged.returncode == 1:
                run(["git", "commit", "-m", f"archive({manifest['agent']}): {run_key}"], cwd=checkout)
                result = subprocess.run(["git", "push", "origin", f"HEAD:refs/heads/{branch}"],
                                        cwd=checkout, text=True, capture_output=True)
                if result.returncode != 0:
                    if any(word in result.stderr.lower() for word in ("non-fast-forward", "fetch first")) and attempt < attempts:
                        print(f"Main moved during upload, rebuilding against latest tree ({attempt}/{attempts})")
                        continue
                    raise RuntimeError("Git push failed (no force): " + result.stderr.strip())
            else:
                raise RuntimeError("Cannot determine git staged diff")
            run(["git", "fetch", "--quiet", "origin", branch], cwd=checkout)
            for name, raw in entries.items():
                remote = run(["git", "show", f"FETCH_HEAD:{name}"], cwd=checkout, capture=True).stdout
                if hashlib.sha256(remote).digest() != hashlib.sha256(raw).digest():
                    raise RuntimeError("Remote fetch mismatch: " + name)
            print("GITHUB_VERIFIED:", run(["git", "rev-parse", "FETCH_HEAD"], cwd=checkout, capture=True).stdout.decode().strip())
            print("Validated:", ", ".join(sorted(entries)))
            print("PAGES_UNVERIFIED: verify site deployment and all public downloads separately")
            return
    raise RuntimeError("Failed to archive after concurrent-main retries")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Clone URL; existing Git credentials required")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()
    manifest, entries = load_bundle(args.bundle)
    print("BUNDLE_VERIFIED:", manifest["run_key"], "formats:", ", ".join(sorted(manifest["files"])))
    publish(manifest, entries, args.repo, args.branch, args.attempts)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print("ARCHIVE_BLOCKED:", exc, file=sys.stderr)
        sys.exit(1)
