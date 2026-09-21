"""Regression tests for the real full-tree catalog/audit scripts.

Fixtures are deliberately synthetic: they verify archival integrity and formats,
not the editorial accuracy of any research report.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
KINDS = {"market": ("MARKET", "0800"), "tech": ("TECH", "0800"), "china": ("CHINA", "2000")}


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        (self.root / "scripts").mkdir()
        (self.root / "reports").mkdir()
        for script in ("build_catalog.py", "audit.py"):
            shutil.copy2(SOURCE / "scripts" / script, self.root / "scripts" / script)
        for name in ("README.md", "AGENTS.md", "index.html", ".nojekyll"):
            (self.root / name).write_text("fixture", encoding="utf-8")
        self.run("build_catalog.py")

    def tearDown(self):
        self.work.cleanup()

    def run(self, script, *args):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / script), *args],
            cwd=self.root, text=True, capture_output=True, check=False,
        )

    def add_report(self, agent="tech", formats=("pdf", "docx", "pptx")):
        prefix, hhmm = KINDS[agent]
        key = f"{prefix}-2026-09-21-{hhmm}"
        directory = self.root / "reports" / agent / "2026" / "09" / "21" / key
        directory.mkdir(parents=True)
        recorded = {}
        for fmt in formats:
            target = directory / f"report.{fmt}"
            if fmt == "pdf":
                target.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF\n")
            else:
                main = "word/document.xml" if fmt == "docx" else "ppt/presentation.xml"
                with zipfile.ZipFile(target, "w") as z:
                    z.writestr("[Content_Types].xml", "<Types />")
                    z.writestr(main, "<doc />")
            raw = target.read_bytes()
            recorded[fmt] = {
                "path": target.relative_to(self.root).as_posix(),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        manifest = {
            "schema_version": 1,
            "run_key": key,
            "agent": agent,
            "date": "2026-09-21",
            "scheduled_time": hhmm[:2] + ":" + hhmm[2:],
            "title": agent + " synthetic fixture",
            "summary": "Integrity test data only",
            "status": "FULL" if len(formats) == 3 else "DEGRADED",
            "files": recorded,
        }
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return directory

    def assert_audit_ok(self):
        check = self.run("build_catalog.py", "--check")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        audit = self.run("audit.py")
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)

    def assert_audit_fails(self, expected_message):
        audit = self.run("audit.py")
        self.assertNotEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        self.assertIn(expected_message, audit.stdout + audit.stderr)

    def test_empty_archive_is_valid(self):
        self.assert_audit_ok()

    def test_three_agents_are_indexed_without_data_loss(self):
        for agent in KINDS:
            self.add_report(agent)
        self.run("build_catalog.py")
        self.assert_audit_ok()
        catalog = json.loads((self.root / "catalog.json").read_text())
        self.assertEqual(len(catalog["reports"]), 3)
        self.assertEqual({x["agent"] for x in catalog["reports"]}, set(KINDS))

    def test_genuine_partial_report_is_marked_degraded(self):
        self.add_report(formats=("pdf",))
        self.run("build_catalog.py")
        self.assert_audit_ok()
        report = json.loads((self.root / "catalog.json").read_text())["reports"][0]
        self.assertEqual(report["status"], "DEGRADED")
        self.assertEqual(set(report["files"]), {"pdf"})

    def test_tampered_attachment_is_rejected(self):
        directory = self.add_report()
        self.run("build_catalog.py")
        (directory / "report.pdf").write_bytes(b"%PDF-1.4\nchanged\n%%EOF")
        self.assert_audit_fails("Attachment bytes/hash mismatch")

    def test_orphan_attachment_is_rejected(self):
        directory = self.add_report()
        self.run("build_catalog.py")
        (directory / "report-copy.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
        self.assert_audit_fails("Orphan or noncanonical file")

    def test_stale_catalog_is_rejected(self):
        self.add_report()
        self.assertNotEqual(self.run("build_catalog.py", "--check").returncode, 0)
        self.assert_audit_fails("Stale/incomplete catalog")

    def test_corrupted_office_package_is_rejected(self):
        directory = self.add_report()
        doc = directory / "report.docx"
        doc.write_bytes(b"not a ZIP package")
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["docx"]["bytes"] = doc.stat().st_size
        manifest["files"]["docx"]["sha256"] = hashlib.sha256(doc.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        self.run("build_catalog.py")
        self.assert_audit_fails("Invalid OOXML ZIP")

    def test_run_folder_and_manifest_disagreement_is_rejected(self):
        directory = self.add_report()
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["date"] = "2026-09-20"
        manifest_path.write_text(json.dumps(manifest))
        self.run("build_catalog.py")
        self.assert_audit_fails("Manifest and folder disagree")


if __name__ == "__main__":
    unittest.main()
