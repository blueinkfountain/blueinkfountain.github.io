"""Install the repaired Daily Record editor without modifying the ink builder."""

from pathlib import Path
import argparse
import shutil
import sys


def backup_once(path: Path):
    if not path.is_file():
        return None
    backup_path = path.with_name(path.name + ".before-record-fix")
    if not backup_path.exists():
        shutil.copy2(path, backup_path)
    return backup_path


def install(repo: Path):
    repo = Path(repo).expanduser().resolve()
    here = Path(__file__).resolve().parent

    builder = repo / "scripts" / "build_untexed_records.py"
    editor = repo / "scripts" / "daily_record.py"
    shell = repo / "update-notes.sh"
    gitignore = repo / ".gitignore"

    for path in (builder, editor, shell):
        if not path.is_file():
            raise FileNotFoundError(f"Expected existing site file: {path}")

    # Avoid installing a note transport incompatible with the actual builder.
    builder_code = builder.read_text(encoding="utf-8")
    if 'DAILY_RECORD_NOTE' not in builder_code:
        raise RuntimeError(
            "Builder does not support DAILY_RECORD_NOTE. "
            "Aborting without modifying the site."
        )

    for path in (editor, shell, gitignore):
        backup_once(path)

    shutil.copy2(here / "daily_record.py", editor)
    shutil.copy2(here / "update-notes.sh", shell)
    shell.chmod(shell.stat().st_mode | 0o111)

    lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.is_file() else []
    for line in (".daily_record_pending.json", ".daily_record_backup/"):
        if line not in lines:
            lines.append(line)
    gitignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return editor, shell, gitignore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    try:
        paths = install(Path(args.repo))
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"Installation canceled: {exc}", file=sys.stderr)
        return 2
    print("Daily Record repaired. Ink builder unchanged.")
    for p in paths:
        print("  " + str(p))
    print("Backups have the suffix .before-record-fix")
    print("Run: update!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
