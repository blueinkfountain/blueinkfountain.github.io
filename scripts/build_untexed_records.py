from pathlib import Path
import hashlib
import yaml

ROOT = Path(__file__).resolve().parents[1]
UNTEXED = ROOT / "untexed"
OUTPUT = ROOT / "_data" / "untexed_records.yml"


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def get_pdf_snapshot(date_dir):
    snapshot = {}

    for path in date_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() == ".pdf":
            relative = path.relative_to(date_dir).as_posix()

            snapshot[relative] = {
                "hash": sha256(path),
                "name": path.name,
            }

    return snapshot


date_dirs = sorted(
    [
        p for p in UNTEXED.iterdir()
        if p.is_dir() and p.name.isdigit()
    ],
    key=lambda p: p.name
)

snapshots = {
    date_dir.name: get_pdf_snapshot(date_dir)
    for date_dir in date_dirs
}

records = {}

for i, date_dir in enumerate(date_dirs):
    date = date_dir.name
    current = snapshots[date]

    # 최초 버전
    if i == 0:
        records[date] = {
            "added": sorted(current.keys()),
            "modified": [],
            "deleted": [],
        }
        continue

    previous_date = date_dirs[i - 1].name
    previous = snapshots[previous_date]

    current_paths = set(current)
    previous_paths = set(previous)

    added = sorted(current_paths - previous_paths)
    deleted = sorted(previous_paths - current_paths)

    common = current_paths & previous_paths

    modified = sorted(
        path
        for path in common
        if current[path]["hash"] != previous[path]["hash"]
    )

    records[date] = {
        "added": added,
        "modified": modified,
        "deleted": deleted,
    }


OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8") as f:
    yaml.safe_dump(
        records,
        f,
        allow_unicode=True,
        sort_keys=False,
    )

print(f"Generated: {OUTPUT}")