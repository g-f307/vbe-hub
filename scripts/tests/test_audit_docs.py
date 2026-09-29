from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit_docs import audit_documentation


class AuditDocumentationTests(unittest.TestCase):
    def test_accepts_indexed_documents_with_valid_local_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (root / "AGENTS.md").write_text(
                "# Contexto\n\nConsulte [documentação](docs/README.md).\n",
                encoding="utf-8",
            )
            (docs / "README.md").write_text(
                "# Documentação\n\nLeia [operações](operations.md).\n",
                encoding="utf-8",
            )
            (docs / "operations.md").write_text(
                "---\nid: OPS-001\ntype: operations\nstatus: active\n"
                "title: Operações\ncreated: 2026-09-28\nupdated: 2026-09-28\n"
                "owner: VBE Hub\nrelated_docs: []\n---\n\n# Operações\n",
                encoding="utf-8",
            )

            issues = audit_documentation(root, strict=True)

            self.assertEqual(issues, [])

    def test_reports_broken_relative_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (root / "AGENTS.md").write_text("# Contexto\n", encoding="utf-8")
            (docs / "README.md").write_text(
                "# Documentação\n\nLeia [ausente](missing.md).\n",
                encoding="utf-8",
            )

            issues = audit_documentation(root, strict=False)

            self.assertEqual(
                issues,
                ["docs/README.md:3: link local inexistente: missing.md"],
            )

    def test_strict_mode_reports_missing_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (root / "AGENTS.md").write_text("# Contexto\n", encoding="utf-8")
            (docs / "README.md").write_text("# Documentação\n", encoding="utf-8")
            (docs / "operations.md").write_text("# Operações\n", encoding="utf-8")

            issues = audit_documentation(root, strict=True)

            self.assertEqual(
                issues,
                ["docs/operations.md: frontmatter YAML obrigatório ausente"],
            )


if __name__ == "__main__":
    unittest.main()
