#!/usr/bin/env python3

from __future__ import annotations

import argparse
import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DIR = ROOT / ".local"
ENV_PATH = LOCAL_DIR / "odoo.env"
CONF_PATH = LOCAL_DIR / "odoo.conf"
ENV_TEMPLATE_PATH = ROOT / "ops" / "examples" / "env.local.example"
CONF_TEMPLATE_PATH = ROOT / "ops" / "templates" / "odoo.conf.local.template"


def random_secret() -> str:
    return secrets.token_urlsafe(24)


def write_if_missing(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.write_text(content, encoding="utf-8")


def render_local_env() -> str:
    return "\n".join(
        [
            "POSTGRES_DB=odoo_local",
            "POSTGRES_USER=odoo",
            f"POSTGRES_PASSWORD={random_secret()}",
            f"ODOO_ADMIN_PASSWORD={random_secret()}",
            "",
        ]
    )


def render_local_conf(env_map: dict[str, str]) -> str:
    content = CONF_TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "__ADMIN_PASSWD__": env_map["ODOO_ADMIN_PASSWORD"],
        "__DB_USER__": env_map["POSTGRES_USER"],
        "__DB_PASSWORD__": env_map["POSTGRES_PASSWORD"],
        "__DB_NAME__": env_map["POSTGRES_DB"],
    }
    for source, target in replacements.items():
        content = content.replace(source, target)
    return content


def parse_env(content: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in content.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    LOCAL_DIR.mkdir(exist_ok=True)
    env_content = render_local_env()
    env_map = parse_env(env_content)
    conf_content = render_local_conf(env_map)

    write_if_missing(ENV_PATH, env_content, force=args.force)
    write_if_missing(CONF_PATH, conf_content, force=args.force)

    print(f"Wrote {ENV_PATH}")
    print(f"Wrote {CONF_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
