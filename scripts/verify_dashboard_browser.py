#!/usr/bin/env python3
"""Headless Chrome E2E: verify a live report is actually rendered in the dashboard.

Requires Google Chrome on the GitHub-hosted Ubuntu runner. This runs only
after deploy + HTTP/hash tests, and captures a real browser screenshot.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", required=True)
    parser.add_argument("--screenshot", required=True, type=Path)
    args = parser.parse_args()
    if not args.site_url.startswith("https://"):
        parser.error("Site URL must use HTTPS")
    browser = next(
        (path for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
         if (path := shutil.which(name))), None
    )
    if browser is None:
        print("BROWSER_UNVERIFIED: no supported Chrome/Chromium binary on runner", file=sys.stderr)
        return 1

    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    if not catalog["reports"]:
        print("BROWSER_VERIFIED: empty archive state, no report card expected")
        return 0
    latest = catalog["reports"][0]
    run_key = latest["run_key"]
    url = args.site_url.rstrip("/") + "/?report=" + urllib.parse.quote(run_key)
    common = [
        browser, "--headless=new", "--no-sandbox", "--disable-gpu",
        "--disable-dev-shm-usage", "--hide-scrollbars",
        "--window-size=1440,1080", "--virtual-time-budget=18000",
    ]
    dom = subprocess.run(
        [*common, "--dump-dom", url], check=False, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=70
    )
    if dom.returncode != 0:
        print("BROWSER_UNVERIFIED: Chrome DOM execution error: " + dom.stderr[-1200:], file=sys.stderr)
        return 1
    html = dom.stdout
    if not html or "报告目录加载失败" in html or "无法读取 catalog.json" in html:
        print("BROWSER_UNVERIFIED: site index/catalog failed inside browser", file=sys.stderr)
        return 1
    if run_key not in html or latest["title"] not in html:
        print("BROWSER_UNVERIFIED: expected report card/detail absent in rendered DOM", file=sys.stderr)
        return 1
    section = re.search(r'<section[^>]*id="detail"[^>]*>', html)
    if section is None or re.search(r"\bhidden\b", section.group(0)):
        print("BROWSER_UNVERIFIED: deep-linked report detail is not visible", file=sys.stderr)
        return 1
    count = 0
    if latest.get("schema_version") == 2:
        raw = (ROOT / latest["files"]["json"]).read_text(encoding="utf-8")
        data = json.loads(raw)
        for signal in data.get("signals", []):
            if signal.get("title") and signal["title"] not in html:
                print(f"BROWSER_UNVERIFIED: signal not rendered: {signal['title']}", file=sys.stderr)
                return 1
            count += 1
        if count and "<svg" not in html:
            print("BROWSER_UNVERIFIED: browser rendered no SVG charts", file=sys.stderr)
            return 1
        if data.get("signals") and "资料截止" not in html:
            print("BROWSER_UNVERIFIED: Markdown narrative not fetched into report pane", file=sys.stderr)
            return 1

    args.screenshot.parent.mkdir(parents=True, exist_ok=True)
    shot = subprocess.run(
        [*common, f"--screenshot={args.screenshot}", url],
        check=False, capture_output=True, text=True, timeout=70
    )
    if shot.returncode != 0 or not args.screenshot.is_file():
        print("BROWSER_UNVERIFIED: screenshot capture failed: " + shot.stderr[-1200:], file=sys.stderr)
        return 1
    raw_png = args.screenshot.read_bytes()
    if not raw_png.startswith(b"\x89PNG\r\n\x1a\n") or len(raw_png) < 10000:
        print("BROWSER_UNVERIFIED: screenshot is empty or invalid PNG", file=sys.stderr)
        return 1

    print(f"BROWSER_VERIFIED: run_key={run_key}, signals={count}, rendered_dom_bytes={len(html.encode('utf-8'))}, screenshot_bytes={len(raw_png)}, url={url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
