# Recover a generated report without duplicate email

The GitHub text-file connector cannot publish a local PDF/DOCX/PPTX merely by writing a path, a placeholder, or a manifest. A `FULL` manifest means that three real, verified attachment formats exist **in the archive**, not that Gmail delivery or GitHub Pages publication succeeded.

## Publish an existing report

Obtain the actual generated `report.pdf`, `report.docx`, `report.pptx` and a matching canonical `manifest.json`, packaged as a ZIP containing only `reports/<agent>/YYYY/MM/DD/<RUN_KEY>/...`. Do not include private recipient addresses, mail contents, credentials, internal work documents, or fake placeholder files. All manifest byte counts and SHA-256 values must match the actual attachment bytes.

On a machine with Python 3, Git and permission to push to this repository, download that ZIP and run:

```bash
python3 scripts/publish_bundle.py /path/to/report-bundle.zip
```

The helper uses your existing Git authentication (never place a token in the ZIP). It independently verifies the ZIP, clones the latest `main`, refuses to overwrite a different archive with the same `RUN_KEY`, rebuilds `catalog.json` from all manifests, runs the global audit and repository unit tests, pushes without `--force` and fetches the remote bytes again for hash verification. Concurrent pushes are retried against a fresh full tree; if authentication, audit, upload or validation fails, the helper stops rather than reporting success.

After `GITHUB_VERIFIED`, separately check the GitHub Pages build, the public catalog and all three direct download URLs. Pages propagation may lag. **Do not resend an existing `RUN_KEY` in Gmail merely to repair GitHub**; check the previous `SENT` record independently. If the environment lacks a working binary upload route or authenticated Git network access, export the verified ZIP, record `ARCHIVE_BLOCKED`, and do not submit only `manifest.json`/`catalog.json` or claim the website is up to date.
