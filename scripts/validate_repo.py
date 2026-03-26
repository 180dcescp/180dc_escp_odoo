#!/usr/bin/env python3

from __future__ import annotations

import ast
import compileall
import sys
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent.parent
ADDONS = ROOT / "addons"


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def validate_python() -> None:
    if not compileall.compile_dir(str(ADDONS), quiet=1, force=True):
        fail("Python compilation failed.")


def validate_manifests() -> None:
    for manifest in sorted(ADDONS.glob("*/__manifest__.py")):
        content = manifest.read_text(encoding="utf-8")
        try:
            value = ast.literal_eval(content)
        except Exception as exc:  # pragma: no cover
            fail(f"Invalid manifest {manifest}: {exc}")
        if not isinstance(value, dict):
            fail(f"Manifest {manifest} does not evaluate to a dict.")


def validate_xml() -> None:
    for xml_file in sorted(ROOT.rglob("*.xml")):
        try:
            ElementTree.parse(xml_file)
        except ElementTree.ParseError as exc:
            fail(f"Invalid XML {xml_file}: {exc}")


def validate_runtime_files() -> None:
    forbidden = [ROOT / ".env", ROOT / "odoo.conf"]
    for path in forbidden:
        if path.exists():
            fail(f"Tracked runtime secret file should not exist in repo root: {path.name}")


def main() -> int:
    validate_runtime_files()
    validate_manifests()
    validate_python()
    validate_xml()
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

