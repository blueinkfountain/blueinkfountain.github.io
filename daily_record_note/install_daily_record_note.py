from pathlib import Path
import argparse
import shutil
import sys

LATEST_RECORD_MARKER = """  Latest Record"""
PREVIOUS_RECORD_MARKER = """                Previous Record"""

PLAIN_RECORD_SPAN = """        <span>
          Record
        </span>"""

LATEST_RECORD_SPAN = """        <span>
          Record{% if latest_record.note %}<span class="record-daily-note">: {{ latest_record.note | escape }}</span>{% endif %}
        </span>"""

PREVIOUS_PLAIN_RECORD_SPAN = """                    <span>
                      Record
                    </span>"""

PREVIOUS_RECORD_SPAN = """                    <span>
                      Record{% if version_record %}{% if version_record.note %}<span class="record-daily-note">: {{ version_record.note | escape }}</span>{% endif %}{% endif %}
                    </span>"""

CSS_BLOCK = """
.record-daily-note {
  display: inline;
  margin-left: 0.08rem;
  font-weight: normal;
  color: #666;
  overflow-wrap: anywhere;
}
""".strip()

CSS_MARKER = """/* =====================================================
   Latest Record
   ===================================================== */"""

def backup_once(path: Path):
    backup = path.with_name(path.name + ".before-daily-record-note")
    if not backup.exists():
        shutil.copy2(path, backup)

def replace_after_marker(text, marker, old, new, label):
    marker_pos = text.find(marker)
    if marker_pos < 0:
        raise RuntimeError(f"Could not find {label} marker.")

    old_pos = text.find(old, marker_pos)
    if old_pos < 0:
        # Already patched is okay.
        if text.find(new, marker_pos) >= 0:
            return text
        raise RuntimeError(f"Could not find {label} Record span.")

    return text[:old_pos] + new + text[old_pos + len(old):]

def patch_untexed(path: Path):
    text = path.read_text(encoding="utf-8")

    # Latest Record: "Record: note"
    text = replace_after_marker(
        text,
        LATEST_RECORD_MARKER,
        PLAIN_RECORD_SPAN,
        LATEST_RECORD_SPAN,
        "Latest Record",
    )

    # Previous -> each expanded historical Record: "Record: note"
    text = replace_after_marker(
        text,
        PREVIOUS_RECORD_MARKER,
        PREVIOUS_PLAIN_RECORD_SPAN,
        PREVIOUS_RECORD_SPAN,
        "Previous Record",
    )

    # Styling.
    if ".record-daily-note {" not in text:
        if CSS_MARKER not in text:
            raise RuntimeError("Could not find Record CSS marker.")
        text = text.replace(
            CSS_MARKER,
            CSS_BLOCK + "\n\n\n" + CSS_MARKER,
            1,
        )

    path.write_text(text, encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        default=".",
        help="math-blog repository root (default: current directory)",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    here = Path(__file__).resolve().parent

    builder_dst = repo / "scripts" / "build_untexed_records.py"
    shell_dst = repo / "update-notes.sh"
    page_dst = repo / "docs" / "Works" / "Untexed.md"

    for path in (builder_dst, shell_dst, page_dst):
        if not path.exists():
            raise SystemExit(f"Missing expected file: {path}")

    # Backup the user's current local files before touching anything.
    for path in (builder_dst, shell_dst, page_dst):
        backup_once(path)

    shutil.copy2(here / "build_untexed_records.py", builder_dst)
    shutil.copy2(here / "update-notes.sh", shell_dst)
    shell_dst.chmod(0o755)

    patch_untexed(page_dst)

    print("Installed Daily Record notes.")
    print()
    print("Changed:")
    print(f"  {builder_dst}")
    print(f"  {shell_dst}")
    print(f"  {page_dst}")
    print()
    print("Backups were saved next to each file with suffix:")
    print("  .before-daily-record-note")
    print()
    print("Now run:")
    print("  update!")
    print()
    print("A text-entry dialog should appear on macOS.")

if __name__ == "__main__":
    main()
