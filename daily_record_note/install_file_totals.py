from pathlib import Path
import argparse
import re
import shutil


TOTAL_HELPERS = r'''
# =========================================================
# Per-file absolute ink totals
# =========================================================

def calculate_file_total_ink_percent(
    date_dir,
    current_snapshot,
    previous_record=None,
    previous_snapshot=None,
):
    # Reuse yesterday's stored total when the rendered PDF is unchanged.
    # Exact visual-hash matches within the same subject also survive rename.
    previous_record = previous_record or {}
    previous_snapshot = previous_snapshot or {}
    previous_totals = dict(
        previous_record.get("file_total_ink_percent", {}) or {}
    )

    old_by_identity = defaultdict(list)
    for old_path, old_info in previous_snapshot.items():
        old_by_identity[
            (
                top_subject(old_path),
                old_info.get("hash"),
            )
        ].append(old_path)

    result = {}

    for path in sorted(current_snapshot):
        current_info = current_snapshot[path]
        current_hash = current_info.get("hash")

        if (
            path in previous_snapshot
            and previous_snapshot[path].get("hash") == current_hash
            and path in previous_totals
        ):
            result[path] = previous_totals[path]
            continue

        identity = (
            top_subject(path),
            current_hash,
        )
        old_candidates = old_by_identity.get(identity, [])

        if len(old_candidates) == 1:
            old_path = old_candidates[0]
            if old_path in previous_totals:
                result[path] = previous_totals[old_path]
                continue

        print(f"File total ink: {path}")
        pixels = count_total_ink_pixels(
            date_dir / Path(path)
        )
        result[path] = rounded_ink_percent(pixels)

    return result


def attach_file_totals_to_record(
    record,
    date_dir,
    current_snapshot,
    previous_record=None,
    previous_snapshot=None,
    include_urls=False,
):
    file_totals = calculate_file_total_ink_percent(
        date_dir,
        current_snapshot,
        previous_record=previous_record,
        previous_snapshot=previous_snapshot,
    )

    record["file_total_ink_percent"] = file_totals

    record["subjects"] = build_subject_tree(
        current_snapshot,
        record.get("file_ink_percent", {}) or {},
        record.get("subject_ink_percent", {}) or {},
        record.get("folder_ink_percent", {}) or {},
        include_urls=include_urls,
        file_total_ink_percent=file_totals,
    )

    return record


'''.lstrip()


MAIN_ATTACH_BLOCK = r'''
    # =====================================================
    # Per-file absolute ink totals
    # =====================================================
    # Frozen history is left untouched. The one-time backfill script fills
    # old frozen records once. Normal update! only maintains mutable dates.
    # =====================================================

    for index, date_dir in enumerate(active_dirs):
        date = date_dir.name
        current = snapshots[date]

        previous_record = None
        previous_snapshot = None

        if index > 0:
            previous_date = active_dirs[index - 1].name
            previous_record = records.get(previous_date)
            previous_snapshot = snapshots.get(previous_date)

        elif anchor_dir is not None:
            previous_date = anchor_dir.name
            previous_record = records.get(previous_date)
            previous_snapshot = snapshots.get(previous_date)

        attach_file_totals_to_record(
            records[date],
            date_dir,
            current,
            previous_record=previous_record,
            previous_snapshot=previous_snapshot,
            include_urls=False,
        )

'''.lstrip("\n")


def patch_builder(text):
    if "def calculate_file_total_ink_percent(" in text:
        return text

    signature_old = '''def build_subject_tree(
    snapshot,
    file_ink_percent,
    subject_ink_percent,
    folder_ink_percent,
    include_urls=False,
):'''
    signature_new = '''def build_subject_tree(
    snapshot,
    file_ink_percent,
    subject_ink_percent,
    folder_ink_percent,
    include_urls=False,
    file_total_ink_percent=None,
):'''

    if signature_old not in text:
        raise RuntimeError("Could not find build_subject_tree signature.")
    text = text.replace(signature_old, signature_new, 1)

    tree_pos = text.find("def build_subject_tree(")
    body_marker = "    subject_nodes = {}\n"
    marker_pos = text.find(body_marker, tree_pos)
    if marker_pos >= 0:
        body_replacement = '''    if file_total_ink_percent is None:
        file_total_ink_percent = {}

    subject_nodes = {}
'''
        text = text[:marker_pos] + body_replacement + text[marker_pos + len(body_marker):]
    else:
        # Fallback for a compact/minimal function body.
        file_item_pos = text.find("    file_item = {", tree_pos)
        if file_item_pos < 0:
            raise RuntimeError("Could not find build_subject_tree body marker.")
        init = '''    if file_total_ink_percent is None:
        file_total_ink_percent = {}

'''
        text = text[:file_item_pos] + init + text[file_item_pos:]

    item_old = '''            "ink_added_percent": file_ink_percent.get(path, 0.0),
        }'''
    item_new = '''            "ink_added_percent": file_ink_percent.get(path, 0.0),
            "total_ink_percent": file_total_ink_percent.get(path),
        }'''
    if item_old not in text:
        raise RuntimeError("Could not find file_item ink field.")
    text = text.replace(item_old, item_new, 1)

    main_marker = '''# =========================================================
# Main
# =========================================================
'''
    if main_marker not in text:
        raise RuntimeError("Could not find Main marker.")
    text = text.replace(main_marker, TOTAL_HELPERS + main_marker, 1)

    sort_marker = '''    # =====================================================
    # Sort Added / Modified by ink amount for display
    # =====================================================
'''
    if sort_marker not in text:
        raise RuntimeError("Could not find sort marker.")
    text = text.replace(sort_marker, MAIN_ATTACH_BLOCK + sort_marker, 1)

    latest_marker = '''        include_urls=True,
    )

    # =====================================================
    # Mirror only newest PDFs into tracked publish directory'''
    latest_replacement = '''        include_urls=True,
        file_total_ink_percent=records[
            latest_date
        ].get(
            "file_total_ink_percent",
            {},
        ),
    )

    # =====================================================
    # Mirror only newest PDFs into tracked publish directory'''
    if latest_marker not in text:
        raise RuntimeError("Could not find latest-tree rebuild.")
    text = text.replace(latest_marker, latest_replacement, 1)

    return text


FILE_INCREMENT_RE = re.compile(
    r'''(?P<indent>[ \t]*)\{%\s*if\s+file\.ink_added_percent\s*>\s*0\s*%\}\s*
(?P=indent)[ \t]*<span\s+class="file-ink">\s*
(?P=indent)[ \t]*\+\{\{\s*file\.ink_added_percent\s*\}\}%\s*ink\s*
(?P=indent)[ \t]*</span>\s*
(?P=indent)\{%\s*endif\s*%\}''',
    re.MULTILINE,
)


def replace_file_increment_blocks(text):
    def repl(match):
        indent = match.group("indent")
        return (
            indent + "{% if file.total_ink_percent != nil %}\n"
            + indent + '  <span class="file-total-ink">\n'
            + indent + "    {{ file.total_ink_percent }}%\n"
            + indent + "  </span>\n"
            + indent + "{% endif %}"
        )

    return FILE_INCREMENT_RE.sub(repl, text)


def patch_untexed_page(text):
    text = replace_file_increment_blocks(text)
    text = text.replace(".file-ink", ".file-total-ink")

    main_rule = re.compile(
        r'''\.file-total-ink\s*\{
(?P<body>.*?)
\}''',
        re.DOTALL,
    )
    match = main_rule.search(text)
    if match:
        replacement = '''.file-total-ink {
  display: inline-block;
  margin-left: 0.38rem;
  font-size: 0.68rem;
  font-weight: normal;
  color: #888;
  white-space: nowrap;
  vertical-align: baseline;
}'''
        text = text[:match.start()] + replacement + text[match.end():]

    return text


def patch_folder_include(text):
    return replace_file_increment_blocks(text)


def backup_once(path, suffix):
    backup = path.with_name(path.name + suffix)
    if not backup.exists():
        shutil.copy2(path, backup)
    return backup


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="math-blog repository root")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    builder = repo / "scripts" / "build_untexed_records.py"
    page = repo / "docs" / "Works" / "Untexed.md"
    include = repo / "_includes" / "untexed_folder.html"

    for path in (builder, page, include):
        if not path.exists():
            raise SystemExit(f"Missing expected file: {path}")

    suffix = ".before-file-total-ink"
    backups = [
        backup_once(builder, suffix),
        backup_once(page, suffix),
        backup_once(include, suffix),
    ]

    builder.write_text(patch_builder(builder.read_text(encoding="utf-8")), encoding="utf-8")
    page.write_text(patch_untexed_page(page.read_text(encoding="utf-8")), encoding="utf-8")
    include.write_text(patch_folder_include(include.read_text(encoding="utf-8")), encoding="utf-8")

    print("Installed per-file absolute ink totals.")
    print("Patched:")
    print(f"  {builder}")
    print(f"  {page}")
    print(f"  {include}")
    print("Backups:")
    for path in backups:
        print(f"  {path}")


if __name__ == "__main__":
    main()
