#!/usr/bin/env python3
"""Verify deployed GitHub Pages homepage, catalog and real latest report files.

This is a *post-deployment* acceptance test, separate from repository CI. It
waits for Pages/CDN propagation, rejects stale indexes, validates bytes/hashes,
and never claims website success from the Actions deploy result alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog.json"


def get_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "cron-news-pages-verifier/1.0", "Cache-Control": "no-cache"}
    )
    with urllib.request.urlopen(request, timeout=22) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}: {url}")
        data = response.read(20_000_001)
        if len(data) > 20_000_000:
            raise ValueError(f"Unexpectedly large public file: {url}")
        return data


def url_for(base: str, relative: str) -> str:
    if relative.startswith("/") or ".." in relative.split("/") or "://" in relative:
        raise ValueError(f"Unsafe relative path: {relative}")
    return urllib.parse.urljoin(base, relative)


def verify_once(site: str, expected: dict) -> tuple[int, int]:
    nonce = os.environ.get("GITHUB_SHA", "public")
    prefix = site.rstrip("/") + "/"
    remote_catalog = json.loads(get_bytes(url_for(prefix, f"catalog.json?qa={nonce}")).decode("utf-8"))
    if remote_catalog != expected:
        raise ValueError("Published catalog differs from the commit; deployment/cache is stale")

    homepage = get_bytes(prefix).decode("utf-8")
    if "<html" not in homepage.lower() or 'id="items"' not in homepage or "assets/dashboard.js" not in homepage:
        raise ValueError("Public homepage missing interactive dashboard shell")
    script = get_bytes(url_for(prefix, "assets/dashboard.js")).decode("utf-8")
    stylesheet = get_bytes(url_for(prefix, "assets/dashboard.css")).decode("utf-8")
    if "catalog.json" not in script or "signal-chart" not in script or len(stylesheet) < 100:
        raise ValueError("Live dashboard JS/CSS is not the expected application")

    checked = 0
    reports = expected.get("reports", [])
    for report in reports[:3]:
        run_key = report["run_key"]
        files = report["files"]
        # Browser-loaded Markdown and JSON are required in v2; old v1 remains download-only.
        if report.get("schema_version") != 2:
            continue
        if set(files) < {"md", "json"}:
            raise ValueError(f"Invalid v2 catalog entry: {run_key}")
        manifest_path = str(Path(files["md"]).parent / "manifest.json")
        local_manifest = json.loads((ROOT / manifest_path).read_text(encoding="utf-8"))
        remote_manifest = json.loads(get_bytes(url_for(prefix, manifest_path)).decode("utf-8"))
        if local_manifest != remote_manifest:
            raise ValueError(f"Manifest unavailable or stale for {run_key}")
        for fmt in ("md", "json"):
            item = local_manifest["files"][fmt]
            raw = get_bytes(url_for(prefix, item["path"]))
            if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError(f"Public attachment byte/hash mismatch: {item['path']}")
            if fmt == "json":
                payload = json.loads(raw.decode("utf-8"))
                if payload.get("run_key") != run_key:
                    raise ValueError("Public data.json identity mismatch")
            checked += 1
    return len(reports), checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", default="https://1998x-stack.github.io/cron-news/")
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--interval", type=float, default=8)
    args = parser.parse_args()
    if not args.site_url.startswith("https://") or args.attempts < 1 or args.interval < 0:
        parser.error("Use HTTPS site URL and nonnegative retry settings")
    expected = json.loads(CATALOG.read_text(encoding="utf-8"))
    for attempt in range(1, args.attempts + 1):
        try:
            count, attachments = verify_once(args.site_url, expected)
            print(f"PAGES_VERIFIED: reports={count}, latest-v2-artifacts={attachments}, url={args.site_url}")
            return 0
        except (OSError, ValueError, UnicodeError, urllib.error.URLError, KeyError) as error:
            print(f"Pages check attempt {attempt}/{args.attempts}: {type(error).__name__}: {error}", flush=True)
            if attempt < args.attempts:
                time.sleep(args.interval)
    print("PAGES_UNVERIFIED: live public website or files failed independent verification", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
