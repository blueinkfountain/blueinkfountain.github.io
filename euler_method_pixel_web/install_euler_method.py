#!/usr/bin/env python3
"""Install the static Euler ODE Lab into the user's existing Jekyll repo."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

FILES = (
    "docs/Works/Euler-Method.html",
    "assets/euler-method/math.mjs",
    "assets/euler-method/pixel.mjs",
    "assets/euler-method/app.mjs",
    "assets/euler-method/style.css",
    "assets/euler-method/preview.html",
)


def install(repo: Path, package: Path):
    config = repo / "_config.yml"
    if not config.is_file():
        raise SystemExit(f"Not a Jekyll repository: {repo}\nExpected: {config}")
    for rel in FILES:
        source = package / rel
        if not source.is_file():
            raise SystemExit(f"Incomplete package; missing: {source}")
    # Local-only backups stay outside assets/ and docs/, so a normal
    # 'git add assets/euler-method/' cannot accidentally publish backups.
    backup_root = repo / ".euler_pixel_backup"
    exclude = repo / ".git" / "info" / "exclude"
    if exclude.is_file():
        ignored = exclude.read_text(encoding="utf-8")
        if "/.euler_pixel_backup/" not in ignored:
            with exclude.open("a", encoding="utf-8") as stream:
                stream.write("\n/.euler_pixel_backup/\n")
    for rel in FILES:
        source = package / rel
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != source.read_bytes():
            backup = backup_root / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                shutil.copy2(target, backup)
                print(f"Backup: {backup}")
        shutil.copy2(source, target)
        print(f"Installed: {rel}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Your Jekyll repository root")
    args = parser.parse_args()
    install(args.repo.expanduser().resolve(), Path(__file__).resolve().parent)
    print("\nReady. Commit and push the new files to publish the Euler Method page.")
    print("Public URL: https://blueinkfountain.github.io/docs/Works/Euler-Method.html")


if __name__ == "__main__":
    main()
