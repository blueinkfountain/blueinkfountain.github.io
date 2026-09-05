from pathlib import Path
import argparse
import os
import shutil


SHELL = r'''#!/bin/sh
set -e

if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

# Fresh run: never reuse a stale note from a previously interrupted update.
rm -f .daily_record_pending_note

echo "Opening Daily Record..."
"$PYTHON" scripts/daily_record.py --repo "$PWD"

if [ -f .daily_record_pending_note ]; then
    DAILY_RECORD_NOTE="$(cat .daily_record_pending_note)"
    export DAILY_RECORD_NOTE
fi

echo
echo "Updating handwritten notes..."
"$PYTHON" scripts/build_untexed_records.py

rm -f .daily_record_pending_note

git add _data/untexed_records.yml
git add -A untexed-current/

echo
echo "Done."
echo "You can now commit normally."
'''

NOTE_BLOCK = r'''    # =====================================================
    # Daily Record note
    # =====================================================
    # Existing notes survive rolling-window recalculation.  The PyQt daily
    # record app stages the newest note through DAILY_RECORD_NOTE so a note can
    # also be attached to a brand-new snapshot that is not yet in YAML.
    for date, record in records.items():
        stored_record = existing_records.get(date) or {}
        stored_note = str(
            stored_record.get("note", "") or ""
        ).strip()

        if stored_note:
            record["note"] = stored_note

    daily_record_note = os.environ.get("DAILY_RECORD_NOTE")

    if daily_record_note is not None:
        daily_record_note = daily_record_note.strip()

        if daily_record_note == "/clear":
            records[latest_date]["note"] = ""
        elif daily_record_note:
            records[latest_date]["note"] = daily_record_note
        else:
            records[latest_date].setdefault(
                "note",
                str(
                    (
                        existing_records.get(latest_date)
                        or {}
                    ).get("note", "")
                    or ""
                ).strip(),
            )

'''

SORT_MARKER = '''    # =====================================================
    # Sort Added / Modified by ink amount for display
    # =====================================================
'''


def backup_once(path):
    backup = path.with_name(path.name + ".before-pyqt-daily-record")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)


def patch_builder(path):
    text = path.read_text(encoding="utf-8")

    if "import os\n" not in text:
        if "import hashlib\n" in text:
            text = text.replace("import hashlib\n", "import hashlib\nimport os\n", 1)
        else:
            text = "import os\n" + text

    if "# Daily Record note" not in text:
        if SORT_MARKER not in text:
            raise RuntimeError(
                "Could not find the Added/Modified sorting marker in "
                "scripts/build_untexed_records.py. No files were overwritten."
            )
        text = text.replace(SORT_MARKER, NOTE_BLOCK + SORT_MARKER, 1)

    path.write_text(text, encoding="utf-8")


def patch_gitignore(path):
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    wanted = [
        ".daily_record_pending_note",
        ".daily_record_backup/",
    ]
    lines = text.splitlines()
    changed = False
    for line in wanted:
        if line not in lines:
            if text and not text.endswith("\n"):
                text += "\n"
            text += line + "\n"
            lines.append(line)
            changed = True
    if changed or not path.exists():
        path.write_text(text, encoding="utf-8")


def install(repo_root, package_root):
    repo_root = Path(repo_root).expanduser().resolve()
    package_root = Path(package_root).expanduser().resolve()

    builder = repo_root / "scripts" / "build_untexed_records.py"
    shell = repo_root / "update-notes.sh"
    gitignore = repo_root / ".gitignore"
    daily_dst = repo_root / "scripts" / "daily_record.py"
    daily_src = package_root / "daily_record.py"

    if not builder.exists():
        raise FileNotFoundError(f"Missing: {builder}")
    if not shell.exists():
        raise FileNotFoundError(f"Missing: {shell}")
    if not daily_src.exists():
        raise FileNotFoundError(f"Missing package file: {daily_src}")

    backup_once(builder)
    backup_once(shell)
    backup_once(gitignore)
    backup_once(daily_dst)

    patch_builder(builder)

    daily_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(daily_src, daily_dst)

    shell.write_text(SHELL, encoding="utf-8")
    shell.chmod(0o755)

    patch_gitignore(gitignore)

    return {
        "daily_record": daily_dst,
        "builder": builder,
        "shell": shell,
        "gitignore": gitignore,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the math-blog repository (default: current directory)",
    )
    args = parser.parse_args()

    package_root = Path(__file__).resolve().parent
    changed = install(args.repo, package_root)

    print("Installed PyQt Daily Record.")
    print()
    for label, path in changed.items():
        print(f"  {label:12}: {path}")
    print()
    print("If PyQt5 is not already installed in the blog virtual environment:")
    print("  .venv/bin/python -m pip install PyQt5")
    print()
    print("Then run:")
    print("  update!")


if __name__ == "__main__":
    main()
