#!/usr/bin/env python3
"""One-time historical backfill for per-file absolute ink totals."""

from pathlib import Path
import argparse
import importlib.util
import shutil

import yaml


def load_builder(repo):
    path = repo / "scripts" / "build_untexed_records.py"
    spec = importlib.util.spec_from_file_location("blueink_build_untexed_records", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot_paths(builder, date_dir):
    snapshot = {}
    for path in sorted(date_dir.rglob("*")):
        if not builder.is_note_pdf(date_dir, path):
            continue
        relative = path.relative_to(date_dir).as_posix()
        snapshot[relative] = {}
    return snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="math-blog repository root")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    output = repo / "_data" / "untexed_records.yml"
    snapshot_root = repo / "untexed"

    if not output.exists():
        raise SystemExit(f"Missing: {output}")
    if not snapshot_root.exists():
        raise SystemExit(f"Missing: {snapshot_root}")

    builder = load_builder(repo)
    if not hasattr(builder, "calculate_file_total_ink_percent"):
        raise SystemExit("Run install_file_totals.py first.")

    with output.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    records = {str(date): record for date, record in (data.get("records", {}) or {}).items()}
    latest_date = str(data.get("latest_date") or "")

    backup = output.with_name(output.name + ".before-file-total-backfill")
    if not backup.exists():
        shutil.copy2(output, backup)

    builder.initialize_ink_calibration()

    completed = 0
    skipped = []

    for date in sorted(records, key=builder.parse_snapshot_date):
        date_dir = snapshot_root / date
        if not date_dir.is_dir():
            skipped.append(date)
            print(f"Skip {date}: local snapshot folder is missing.")
            continue

        print()
        print("=" * 70)
        print(f"Backfill file totals: {date}")
        print("=" * 70)

        snapshot = snapshot_paths(builder, date_dir)
        totals = {}

        for relative_path in sorted(snapshot):
            print(f"  {relative_path}")
            pixels = builder.count_total_ink_pixels(date_dir / Path(relative_path))
            totals[relative_path] = builder.rounded_ink_percent(pixels)

        record = records[date]
        record["file_total_ink_percent"] = totals
        record["subjects"] = builder.build_subject_tree(
            snapshot,
            record.get("file_ink_percent", {}) or {},
            record.get("subject_ink_percent", {}) or {},
            record.get("folder_ink_percent", {}) or {},
            include_urls=(date == latest_date),
            file_total_ink_percent=totals,
        )
        completed += 1

    data["records"] = records

    with output.open("w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False, width=180)

    print()
    print("=" * 70)
    print("Backfill complete")
    print("=" * 70)
    print(f"Updated dates : {completed}")
    print(f"Skipped dates : {len(skipped)}")
    if skipped:
        print("Missing local snapshots:")
        for date in skipped:
            print(f"  {date}")
    print(f"Backup        : {backup}")
    print(f"Updated YAML  : {output}")
    print("This was a one-time script. It is safe to delete this file now.")


if __name__ == "__main__":
    main()
