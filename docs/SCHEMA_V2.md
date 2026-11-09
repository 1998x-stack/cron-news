# Structured research archive schema v2

This document defines **new** public report bundles. Existing schema-v1 binary-only archives are read-only and remain supported by catalog and Pages. It is not a publication-success record.

## Taxonomy and run keys

- `market`: 08:00, 12:00, 20:00 existing research, plus 20:30 dedicated News Lianbo/A-share research. `MARKET-YYYY-MM-DD-2030`.
- `tech`: existing technology/AI research. `TECH-YYYY-MM-DD-0800`.
- `china`: existing Chinese policy/media research. `CHINA-YYYY-MM-DD-0800|2000`.

Each run is immutable and idempotent at `reports/<agent>/YYYY/MM/DD/<RUN_KEY>/`. Only `manifest.json`, `report.md`, `data.json`, and optional genuine `report.pdf`, `report.docx`, `report.pptx` are permitted.

## manifest.json (schema_version = 2)

```json
{
  "schema_version": 2,
  "run_key": "MARKET-2026-11-10-2030",
  "agent": "market",
  "date": "2026-11-10",
  "scheduled_time": "20:30",
  "title": "示例：新闻联播与市场日报",
  "summary": "仅为格式示例，不是实际市场报告",
  "status": "DEGRADED",
  "files": {
    "md": {
      "path": "reports/market/2026/11/10/MARKET-2026-11-10-2030/report.md",
      "bytes": 1234,
      "sha256": "<real lowercase 64-character hex digest>"
    },
    "json": {
      "path": "reports/market/2026/11/10/MARKET-2026-11-10-2030/data.json",
      "bytes": 1234,
      "sha256": "<real lowercase 64-character hex digest>"
    }
  }
}
```

The above is a **non-publishable schematic**: `bytes` and digest MUST be replaced with measured real values. `PUBLISHED` denotes sufficiently supported research, not deployed Pages. `DEGRADED` denotes partial evidence; neither is an archival or deployment confirmation. Optional binary files are added to `files` only after real bytes and content signatures are validated. No "fake PDF" wrappers.

## data.json (schema_version = 1)

Fields required by the visualization contract:

```json
{
  "schema_version": 1,
  "run_key": "MARKET-2026-11-10-2030",
  "agent": "market",
  "as_of": "2026-11-10T20:30:00+08:00",
  "market_date": null,
  "signals": [],
  "indices": [],
  "sources": [],
  "quality": {
    "status": "PARTIAL",
    "gaps": ["This is a schema example only"]
  }
}
```

For a **real PUBLISHED report**, `sources` must contain at least one actually checked `{title,url}` object. Signal items use `{title,score,confidence,summary,sources}`; scored signals contain a genuine 1–10 numerical score, and unscorable signals use JSON `null`. Market items use `{name,value,change_pct,as_of,source_url}`; unknown numeric values use JSON `null`, **never zero**. Times and trade-session dates must not be conflated.

The browser draws charts only for numeric (not null) observations; no interpolation or prediction is implied. The full Markdown research must contain direct source references, evidence limitations and counterarguments.

## Transactional release protocol

1. Fetch latest main and complete report tree; check run-key collision and public safety.
2. Generate frozen `report.md`, `data.json`, compute true SHA-256/byte lengths and emit the manifest.
3. Build `catalog.json` from **all** manifests with `scripts/build_catalog.py`, then run `--check`, `scripts/audit.py`, and repository unit tests on the complete prospective tree.
4. Commit all new artifacts + deterministic catalog in one fast-forward transaction; rebuild on concurrent-main movement. No force push and no individual manifest-only writes.
5. GitHub Actions `.github/workflows/pages.yml` on main push audits then deploys. Verify deployment run SHA and public URLs separately; allow `PAGES_PENDING` when not yet propagated.
6. If authentication, audit, real report content, URL source provenance, or commit verification is missing, record `ARCHIVE_BLOCKED`; do not claim Pages publication. The ChatGPT schedule is independent of GitHub Actions.

Security: public repository only; no tokens, email recipients, confidential files, personal information or copyrighted full text. All sources should be short quotations and paraphrases with URLs. This schema supports incremental audit, not a substitute for editorial accuracy.
