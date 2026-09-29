from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]*]\(([^)]+)\)")


def _maintained_documents(root: Path) -> list[Path]:
    documents = [root / "AGENTS.md", root / "README.md"]
    docs_root = root / "docs"
    if docs_root.is_dir():
        documents.extend(sorted(docs_root.rglob("*.md")))
    return [path for path in documents if path.is_file()]


def _link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0]


def _is_frontmatter_exempt(path: Path, root: Path) -> bool:
    return path in {root / "AGENTS.md", root / "README.md"} or path.name == "README.md"


def audit_documentation(root: Path, *, strict: bool) -> list[str]:
    """Return documentation problems relative to *root*."""

    root = root.resolve()
    issues: list[str] = []
    for path in _maintained_documents(root):
        relative_path = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8")

        if strict and not _is_frontmatter_exempt(path, root) and not content.startswith("---\n"):
            issues.append(f"{relative_path}: frontmatter YAML obrigatório ausente")

        for line_number, line in enumerate(content.splitlines(), start=1):
            for match in MARKDOWN_LINK.finditer(line):
                target = _link_target(match.group(1))
                parsed = urlsplit(target)
                if not target or target.startswith("#") or parsed.scheme or parsed.netloc:
                    continue
                local_target = unquote(parsed.path)
                if not local_target:
                    continue
                resolved = (path.parent / local_target).resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    issues.append(
                        f"{relative_path}:{line_number}: link sai da raiz: {local_target}"
                    )
                    continue
                if not resolved.exists():
                    issues.append(
                        f"{relative_path}:{line_number}: link local inexistente: {local_target}"
                    )
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audita a documentação mantida do VBE Hub")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true")
    arguments = parser.parse_args(argv)

    issues = audit_documentation(arguments.root, strict=arguments.strict)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    print("Documentação válida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
