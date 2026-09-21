# cron-news | Research intelligence archive

A public, versioned archive for three scheduled research agents. **GitHub is the document archive; Notion is not part of the pipeline.** Reports are informational and not investment advice.

## Agents and cadence (Asia/Shanghai)

| Agent | RUN_KEY prefix | Schedule | Scope |
| --- | --- | --- | --- |
| Market & News Lianbo | `MARKET` | Daily 08:00, 12:00, 20:00 | Global markets, China policy, market evidence, sectors and companies |
| CS & AI Research | `TECH` | Daily 08:00 | AI/Agent, papers, open-source evidence and cross-CS knowledge |
| China Media Research | `CHINA` | Daily 08:00, 20:00 | China economy, society, policy and international media comparison |

## Canonical storage

```text
cron-news/
├── README.md                 # Human-facing project introduction
├── AGENTS.md                 # Mandatory agent publishing and cleanup contract
├── index.html                # GitHub Pages landing page
├── catalog.json              # Generated report index, never hand-edited
├── .nojekyll                 # Serve the repository as static content
├── .github/workflows/audit.yml
├── scripts/build_catalog.py  # Deterministic report index generator
├── scripts/audit.py          # Document-entropy and link integrity guard
└── reports/
    ├── market/YYYY/MM/DD/MARKET-YYYY-MM-DD-HHMM/
    ├── tech/YYYY/MM/DD/TECH-YYYY-MM-DD-0800/
    └── china/YYYY/MM/DD/CHINA-YYYY-MM-DD-HHMM/
        ├── manifest.json
        ├── report.pdf         # When successfully generated
        ├── report.docx        # When successfully generated
        └── report.pptx        # When successfully generated
```

Each scheduled run has exactly **one canonical directory** and **one manifest**. No root-level report attachments, alternative directories, version suffixes (`final`, `v2`, `copy`) or duplicate publications. A failed format must be recorded as missing in the manifest, never linked as if it exists. Never overwrite a past run with a different run key. Historical reports are immutable except for a documented correction of the same run.

## Pages

After the files are committed, configure **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` → Folder: `/(root)` → Save**. Site URL after GitHub finishes publication: `https://1998x-stack.github.io/cron-news/`. The root `index.html` reads `catalog.json` and lists verified PDF, Word and PowerPoint links. An empty catalog means no reports have been archived yet; it is not a publishing error.

## Publishing a run

1. Create the canonical run directory and write its generated report attachments. A document exists in the manifest only after upload/download and format validation succeeds.
2. Write `manifest.json` with schema version `1`, exact run key, agent, date/time, factual summary, publication status, and a `files` mapping with present relative paths, sizes and SHA-256 hashes. Do not write secrets or personal data; everything in this public repository is public.
3. Update `catalog.json` by running `python3 scripts/build_catalog.py`, not by freeform appending entries. Run `python3 scripts/audit.py` and resolve every error **before** the archival commit. If the audit fails, do not claim the archive is complete.
4. Commit run files, the regenerated catalog and any necessary repairs atomically when possible. Confirm the commit and that links resolve. Then send Gmail once using the run key; if attachment/email delivery fails, report it distinctly from repository archival success.
5. On every subsequent run, check the *entire archive* for folder drift, orphan files, duplicate run keys, stale indexes, missing reports, broken links and unexpected binary types. Never fix by deleting or relocating historical files without checking existing references and recording the migration.

See [AGENTS.md](AGENTS.md) for the binding contract and the tools in [`scripts/`](scripts/). The website is a public browse/download interface, not a private document store.
