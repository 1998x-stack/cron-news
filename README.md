# cron-news · Research intelligence archive

Three scheduled research agents publish **public, validated** market, computer science, and China-media reports to one canonical GitHub archive. Notion is not used. No private correspondence, credentials, employer materials, personal data, or copyrighted full texts belong in this public repository.

## Schedule (Asia/Shanghai)

| Agent | RUN_KEY | Time | Coverage | Canonical public Prompt |
| --- | --- | --- | --- | --- |
| Market & News Lianbo | `MARKET-YYYY-MM-DD-HHMM` | Daily 08:00, 12:00, 20:00, **20:30** | Global markets, official China policy, price evidence and sectors | [market.md](prompts/market.md) |
| CS & AI Research | `TECH-YYYY-MM-DD-0800` | Daily 08:00 | AI/Agent, papers, open source, cross-CS engineering | [tech.md](prompts/tech.md) |
| China Media Research | `CHINA-YYYY-MM-DD-HHMM` | Daily 08:00, 20:00 | China economy, society, policy and international media comparison | [china.md](prompts/china.md) |

**Prompt loading order:** latest `main` → `README.md` → [`AGENTS.md`](AGENTS.md) → [`prompts/README.md`](prompts/README.md) → relevant `prompts/<agent>.md`. `AGENTS.md` governs shared safety, archive layout and delivery; the agent-specific file governs its research workflow. ChatGPT scheduled tasks contain their own triggering schedule and **private** recipient settings; no private addresses should be copied to this public repository. Changing a Markdown schedule does not itself update the live timer; when editing prompts, keep the corresponding ChatGPT task aligned.

## Canonical file layout

```text
cron-news/
├── README.md
├── AGENTS.md                    # Mandatory policy for all three agents
├── prompts/
│   ├── README.md                # Prompt ownership, update and privacy contract
│   ├── market.md                # Market & News Lianbo research Prompt
│   ├── tech.md                  # CS & AI research Prompt
│   └── china.md                 # China media research Prompt
├── index.html                   # GitHub Pages interactive dashboard
├── catalog.json                 # Machine-generated from ALL manifests
├── assets/dashboard.css         # Responsive visual interface
├── assets/dashboard.js          # Safe charts from structured JSON
├── .nojekyll
├── .github/workflows/
│   ├── audit.yml                # Validates each push and pull request
│   └── pages.yml                # Validates BEFORE deploying GitHub Pages
├── scripts/
│   ├── build_catalog.py
│   └── audit.py
├── tests/                       # Archive and Prompt regression tests
└── reports/
    ├── market/YYYY/MM/DD/MARKET-YYYY-MM-DD-HHMM/
    ├── tech/YYYY/MM/DD/TECH-YYYY-MM-DD-0800/
    └── china/YYYY/MM/DD/CHINA-YYYY-MM-DD-HHMM/
        ├── manifest.json         # v1/v2 verified metadata
        ├── report.md             # v2 required sourced research
        ├── data.json             # v2 required structured data
        ├── report.pdf            # v2 optional genuine binary
        ├── report.docx           # v2 optional
        └── report.pptx           # v2 optional
```

Every completed report belongs to exactly one run directory. A `manifest.json` records public metadata and the actual formats present, using their exact repository-relative path, byte length, and SHA-256. In schema v2, report.md and data.json are mandatory; genuine PDF/Word/PPTX files are optional. Existing schema v1 archives remain valid and downloadable. Missing formats are not linked. Past runs must not be overwritten or moved without an audited, documented migration. Do not create `latest`, `final`, `copy`, or alternate directories. An email-only fallback does not count as GitHub archival success.

## GitHub Pages

The website is built by `.github/workflows/pages.yml` and deployment is gated on archive and Prompt regression checks. GitHub Pages is configured to deploy with **GitHub Actions** (not “Deploy from a branch”). If a new repository has not enabled Pages, its owner must open **Settings → Pages → Build and deployment → Source: GitHub Actions**. Check the actual site URL and deployments rather than assuming a workflow file means publication succeeded: <https://1998x-stack.github.io/cron-news/>. The homepage reads `catalog.json` and provides PDF, Word and PowerPoint links only for actually archived formats; an empty archive displays no reports.

The Pages artifact includes only `index.html`, `assets/`, `catalog.json`, `README.md`, `AGENTS.md`, `.nojekyll`, and `reports/`. Neither private delivery settings nor Prompt files are included in the website artifact; the public Prompt files remain reviewable in GitHub. Confirm the site's actual URL and report links after each deployment; publication can lag behind the source commit.

## Publishing one run

1. At execution start, read the latest `README.md`, `AGENTS.md`, `prompts/README.md` and the matching `prompts/<agent>.md`. Research with primary sources, review counter-evidence, then produce a sourced Markdown narrative and structured JSON for v2; optionally create genuine DOCX/PDF/PPTX files if feasible. Check that all content is safe for publication in a public repository.
2. Fetch the complete current `main` report tree and stage a single canonical run directory. Upload real Markdown/JSON text files and optional binary files through an authorized binary-capable GitHub API or Git transport; validate signatures/OOXML structures and downloaded bytes where applicable. A UTF-8 file writer cannot upload a PDF or Office binary just by giving it a `.pdf`, `.docx`, or `.pptx` extension.
3. Write `manifest.json` with exact verified filenames, sizes and SHA-256; generate `catalog.json` from **every** manifest using `python3 scripts/build_catalog.py`. Do not append a single new entry manually or remove other agents' entries.
4. Run `python3 scripts/build_catalog.py --check`, `python3 scripts/audit.py` and `python3 -m unittest discover -s tests -v` on the **complete local checkout**, including the new run, BEFORE committing. Resolve all errors; do not publish an unvalidated or partially indexed run.
5. At 08:00 all three agents may publish concurrently. Recheck the current `main` SHA before pushing. If it has changed, update the local tree with all other agents' work, rebuild the catalog, and repeat the full audit. Commit only via a non-forced fast-forward update. Never overwrite another run's manifest or report.
6. Verify the GitHub commit and each actual PDF/DOCX/PPTX link, then verify the GitHub Pages deployment and page links. Distinguish GitHub archival, Pages publication, and one-time Gmail delivery as separate statuses. Gmail must use the exact RUN_KEY as its deduplication key and never blindly resend an uncertain delivery.
7. Every execution must check the complete archive for duplicated run keys, noncanonical placement, unindexed binaries, missing files, file-size/hash inconsistencies, stale indexes, broken links, and unexpected changes to historical material. Review private-information risks manually as well as with automatic checks. Report any blocker rather than claiming an unverified success.

See [AGENTS.md](AGENTS.md) for the mandatory shared contract and [prompts/README.md](prompts/README.md) for Prompt ownership and versioning. Reports are informational, not investment advice.

## 20:30 新闻联播 × A 股专项（v4）

- Existing MARKET 08:00 / 12:00 / 20:00 reports are **not replaced**. The dedicated 20:30 task uses `MARKET-YYYY-MM-DD-2030` in the same `reports/market/` taxonomy.
- A run must publish a sourced `report.md`, structured `data.json`, and checksum `manifest.json` when a substantive report can be verified. PDF/DOCX/PPTX are optional, never renamed placeholders.
- `data.json` uses `schema_version: 1`, `run_key`, `agent`, `as_of` (Beijing ISO 8601), `signals`, `indices`, `sources`, and `quality`. Missing numeric values stay `null`, never fabricated 0.
- Timeline and charts use those actual fields. News broadcast at 19:00 cannot be falsely assigned causal responsibility for A-share returns measured at 15:00 on the same day.
- Publication pipeline: evidence and counter-evidence → freeze artifacts → regenerate global catalog → full-tree tests/audit → optimistic GitHub commit → Pages push trigger → verify deployment and public URLs. No GitHub access or no complete audit means ARCHIVE_BLOCKED, not success.
- Pages deploy is an independent asynchronous GitHub Actions workflow; status `GITHUB_VERIFIED` does not imply `PAGES_VERIFIED`. No extra Actions scheduler should be created.
