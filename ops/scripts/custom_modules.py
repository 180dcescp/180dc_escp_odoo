#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path


def module_names(addons_dir: Path) -> list[str]:
    modules = []
    seen = set()
    for manifest in sorted(addons_dir.rglob("__manifest__.py")):
        path = manifest.parent
        if path.name in seen:
            continue
        seen.add(path.name)
        modules.append(path.name)
    return modules


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--addons-dir", default="addons")
    parser.add_argument("--csv", action="store_true")
    args = parser.parse_args()

    modules = module_names(Path(args.addons_dir).resolve())
    if args.csv:
        print(",".join(modules))
    else:
        print("\n".join(modules))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
