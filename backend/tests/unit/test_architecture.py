import ast
from pathlib import Path


def test_domain_does_not_import_outer_layers() -> None:
    domain_root = Path("src/vbe_hub/domain")
    forbidden_prefixes = (
        "vbe_hub.adapters",
        "vbe_hub.api",
        "vbe_hub.infrastructure",
    )
    violations: list[str] = []

    for source_file in domain_root.rglob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        imported_modules = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        imported_modules.extend(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        violations.extend(
            f"{source_file}: {module}"
            for module in imported_modules
            if module.startswith(forbidden_prefixes)
        )

    assert violations == []
