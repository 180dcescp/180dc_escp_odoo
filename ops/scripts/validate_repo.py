#!/usr/bin/env python3

from __future__ import annotations

import ast
import compileall
import sys
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "addons"
DOCS = ROOT / "docs"
REQUIRED_DOCS = [
    ROOT / "CHANGELOG.md",
    DOCS / "architecture.md",
    DOCS / "install.md",
    DOCS / "publishing.md",
    DOCS / "dependency_matrix.md",
    DOCS / "upgrades.md",
]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def manifest_files() -> list[Path]:
    return sorted(path for path in ADDONS.rglob("__manifest__.py") if "__pycache__" not in path.parts)


def validate_python() -> None:
    if not compileall.compile_dir(str(ADDONS), quiet=1, force=True):
        fail("Python compilation failed.")
    if not compileall.compile_dir(str(ROOT / "ops"), quiet=1, force=True):
        fail("Ops Python compilation failed.")


def validate_manifests() -> None:
    for manifest in manifest_files():
        content = manifest.read_text(encoding="utf-8")
        try:
            value = ast.literal_eval(content)
        except Exception as exc:  # pragma: no cover
            fail(f"Invalid manifest {manifest}: {exc}")
        if not isinstance(value, dict):
            fail(f"Manifest {manifest} does not evaluate to a dict.")


def validate_xml() -> None:
    for xml_file in sorted(ROOT.rglob("*.xml")):
        if "__pycache__" in xml_file.parts:
            continue
        try:
            ElementTree.parse(xml_file)
        except ElementTree.ParseError as exc:
            fail(f"Invalid XML {xml_file}: {exc}")


def validate_runtime_files() -> None:
    forbidden = [ROOT / ".env", ROOT / "odoo.conf"]
    for path in forbidden:
        if path.exists():
            fail(f"Tracked runtime secret file should not exist in repo root: {path.name}")


def validate_product_packaging() -> None:
    for manifest in manifest_files():
        addon_dir = manifest.parent
        addon_name = addon_dir.name
        if not addon_name.startswith("student_consultancy_"):
            continue
        for required in [
            addon_dir / "README.rst",
            addon_dir / "static" / "description" / "index.html",
        ]:
            if not required.exists():
                fail(f"Missing product packaging file: {required}")
        if addon_name != "student_consultancy_meta":
            test_dir = addon_dir / "tests"
            if not test_dir.is_dir():
                fail(f"Missing tests directory: {test_dir}")


def validate_docs() -> None:
    for path in REQUIRED_DOCS:
        if not path.exists():
            fail(f"Missing documentation file: {path}")


def main() -> int:
    validate_runtime_files()
    validate_manifests()
    validate_python()
    validate_xml()
    validate_product_packaging()
    validate_docs()
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
