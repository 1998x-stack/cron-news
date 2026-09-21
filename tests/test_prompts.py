"""Regression guard for the three canonical public scheduled-agent prompts."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"
EXPECTED = {
    "market": ("MARKET-YYYY-MM-DD-HHMM", "08:00", "12:00", "20:00"),
    "tech": ("TECH-YYYY-MM-DD-0800", "08:00"),
    "china": ("CHINA-YYYY-MM-DD-HHMM", "08:00", "20:00"),
}


class PromptContractTests(unittest.TestCase):
    def test_only_three_canonical_agent_prompts(self):
        self.assertEqual({p.name for p in PROMPTS.glob("*.md")}, {"README.md", "market.md", "tech.md", "china.md"})

    def test_common_rules_and_navigation(self):
        index = (PROMPTS / "README.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for agent in EXPECTED:
            self.assertIn(f"{agent}.md", index)
        self.assertIn("AGENTS.md", index)
        self.assertIn("prompts", index)
        self.assertIn("Notion", agents)

    def test_prompts_are_structured_and_safe_for_public_repo(self):
        for agent, markers in EXPECTED.items():
            with self.subTest(agent=agent):
                content = (PROMPTS / f"{agent}.md").read_text(encoding="utf-8")
                for marker in (*markers, "AGENTS.md", "manifest.json", "catalog.json", "Gmail", "Notion", "SHA-256"):
                    self.assertIn(marker, content)
                for stage in ("## 0.", "## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7."):
                    self.assertIn(stage, content)
                self.assertNotRegex(content, r"(?i)[\w.+-]+@[\w.-]+\.[a-z]{2,}")
                self.assertNotIn("2484230700", content)
                self.assertNotIn("xieminghack", content)


if __name__ == "__main__":
    unittest.main()
