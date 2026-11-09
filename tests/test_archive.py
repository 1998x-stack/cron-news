"""End-to-end tests for full-tree archive/catalog integrity; fixtures are synthetic."""
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
        self.run_script("build_catalog.py")

    def tearDown(self):
        self.work.cleanup()

    def run_script(self, script, *args):
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
        check = self.run_script("build_catalog.py", "--check")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        audit = self.run_script("audit.py")
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)

    def assert_audit_fails(self, expected_message):
        audit = self.run_script("audit.py")
        self.assertNotEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        self.assertIn(expected_message, audit.stdout + audit.stderr)

    def test_empty_archive_is_valid(self):
        self.assert_audit_ok()

    def test_three_agents_are_indexed_without_data_loss(self):
        for agent in KINDS:
            self.add_report(agent)
        self.run_script("build_catalog.py")
        self.assert_audit_ok()
        catalog = json.loads((self.root / "catalog.json").read_text())
        self.assertEqual(len(catalog["reports"]), 3)
        self.assertEqual({x["agent"] for x in catalog["reports"]}, set(KINDS))

    def test_genuine_partial_report_is_marked_degraded(self):
        self.add_report(formats=("pdf",))
        self.run_script("build_catalog.py")
        self.assert_audit_ok()
        report = json.loads((self.root / "catalog.json").read_text())["reports"][0]
        self.assertEqual(report["status"], "DEGRADED")
        self.assertEqual(set(report["files"]), {"pdf"})

    def test_tampered_attachment_is_rejected(self):
        directory = self.add_report()
        self.run_script("build_catalog.py")
        (directory / "report.pdf").write_bytes(b"%PDF-1.4\nchanged\n%%EOF")
        self.assert_audit_fails("Attachment bytes/hash mismatch")

    def test_orphan_attachment_is_rejected(self):
        directory = self.add_report()
        self.run_script("build_catalog.py")
        (directory / "report-copy.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
        self.assert_audit_fails("Orphan or noncanonical file")

    def test_stale_catalog_is_rejected(self):
        self.add_report()
        self.assertNotEqual(self.run_script("build_catalog.py", "--check").returncode, 0)
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
        self.run_script("build_catalog.py")
        self.assert_audit_fails("Invalid OOXML ZIP")

    def test_run_folder_and_manifest_disagreement_is_rejected(self):
        directory = self.add_report()
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["date"] = "2026-09-20"
        manifest_path.write_text(json.dumps(manifest))
        self.run_script("build_catalog.py")
        self.assert_audit_fails("Manifest and folder disagree")


    def add_structured_market(self):
        """A real v2 report contains sourceable Markdown + JSON, not fake binaries."""
        key = "MARKET-2026-09-21-2030"
        directory = self.root / "reports" / "market" / "2026" / "09" / "21" / key
        directory.mkdir(parents=True, exist_ok=True)
        narrative = "# 市场及新闻联播研究日报\n\n" + (
            "本报告用于校验归档格式与实际来源，所有内容均为测试合成材料，不包含真实市场观点。\n"
            "测试版本只核对可追溯来源、文件字节、哈希与结构化元数据，不构建虚假收益预测。\n" * 3
        )
        detail = {
            "schema_version": 1,
            "run_key": key, "agent": "market", "as_of": "2026-09-21T20:30:00+08:00",
            "market_date": None, "signals": [],
            "indices": [{"name": "synthetic missing", "value": None, "change_pct": None,
                         "as_of": "2026-09-21", "source_url": "https://example.org"}],
            "sources": [{"title": "synthetic fixture", "url": "https://example.org"}],
            "quality": {"status": "PARTIAL", "gaps": ["synthetic test only"]},
        }
        payload = {"md": narrative.encode("utf-8"),
                   "json": (json.dumps(detail, ensure_ascii=False, indent=2) + "\n").encode("utf-8")}
        filenames = {"md": "report.md", "json": "data.json"}
        files = {}
        for fmt, raw in payload.items():
            target = directory / filenames[fmt]
            target.write_bytes(raw)
            files[fmt] = {"path": target.relative_to(self.root).as_posix(),
                          "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        manifest = {"schema_version": 2, "run_key": key, "agent": "market",
                    "date": "2026-09-21", "scheduled_time": "20:30",
                    "title": "Synthetic research fixture", "summary": "Published fixture for tests",
                    "status": "PUBLISHED", "files": files}
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return directory

    def test_structured_v2_with_null_market_data_is_valid(self):
        self.add_structured_market()
        self.run_script("build_catalog.py")
        self.assert_audit_ok()
        catalog = json.loads((self.root / "catalog.json").read_text())
        self.assertEqual(catalog["schema_version"], 2)
        self.assertEqual(set(catalog["reports"][0]["files"]), {"md", "json"})

    def test_structured_v2_rejects_mismatched_json_identity(self):
        directory = self.add_structured_market()
        detail_path = directory / "data.json"
        detail = json.loads(detail_path.read_text(encoding="utf-8"))
        detail["run_key"] = "MARKET-2026-09-20-2030"
        detail_path.write_text(json.dumps(detail), encoding="utf-8")
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw = detail_path.read_bytes()
        manifest["files"]["json"]["bytes"] = len(raw)
        manifest["files"]["json"]["sha256"] = hashlib.sha256(raw).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.run_script("build_catalog.py")
        self.assert_audit_fails("Invalid data.json identity/schema")


if __name__ == "__main__":
    unittest.main()
