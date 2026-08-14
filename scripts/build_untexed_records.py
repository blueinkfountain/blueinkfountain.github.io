from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher
import hashlib
import re

import fitz
import yaml


# =========================================================
# Paths
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

UNTEXED = ROOT / "untexed"

OUTPUT = ROOT / "_data" / "untexed_records.yml"


# =========================================================
# Rename detection threshold
#
# 완전히 다른 이름의 파일을 억지로 연결하지 않도록
# 보수적으로 판정한다.
# =========================================================

RENAME_SIMILARITY_THRESHOLD = 0.80


# =========================================================
# .pdf 확장자 제거
#
# foo.pdf       -> foo
# foo.pdf.pdf   -> foo
# foo.PDF.PDF   -> foo
# =========================================================

def strip_pdf_suffixes(name):

    result = name

    while result.lower().endswith(".pdf"):
        result = result[:-4]

    return result


# =========================================================
# Record에 표시할 경로
#
# Algebra/A.pdf
# ->
# Algebra/A
#
# Algebra/A.pdf.pdf
# ->
# Algebra/A
# =========================================================

def display_path(relative_path):

    parts = relative_path.split("/")

    cleaned_parts = []

    for part in parts:

        # 마지막의 .pdf / .pdf.pdf 제거
        part = strip_pdf_suffixes(part)

        # "1. Linear Algebra" -> "Linear Algebra"
        # "3. Finite Group Theory" -> "Finite Group Theory"
        part = re.sub(
            r"^\d+\.\s*",
            "",
            part
        )

        cleaned_parts.append(part)

    return "/".join(cleaned_parts)

# =========================================================
# 비교용 파일명 정규화
# =========================================================

def normalized_filename(relative_path):

    filename = Path(relative_path).name

    filename = strip_pdf_suffixes(filename)

    filename = filename.lower()

    filename = re.sub(
        r"[\s_\-()]+",
        " ",
        filename
    )

    filename = filename.strip()

    return filename


# =========================================================
# 최상위 subject
#
# Algebra/1. Linear Algebra/A.pdf
# ->
# Algebra
# =========================================================

def top_subject(relative_path):

    parts = relative_path.split("/")

    if parts:
        return parts[0]

    return ""


# =========================================================
# PDF의 실제 화면 결과를 hash
#
# PDF binary 자체를 비교하지 않는다.
#
# 따라서 다음 차이는 무시:
#
# - PDF metadata
# - 생성일
# - 수정일
# - Producer
# - object 번호
# - 압축 방식
#
# 실제 페이지의 픽셀 결과가 다를 때만
# hash가 변경된다.
# =========================================================

def visual_pdf_hash(path):

    h = hashlib.sha256()

    document = None

    try:

        document = fitz.open(path)

        # 페이지 수
        h.update(
            str(document.page_count).encode("utf-8")
        )

        for page_number in range(document.page_count):

            page = document.load_page(page_number)

            # 약 144 DPI
            matrix = fitz.Matrix(2.0, 2.0)

            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )

            # 페이지 크기
            h.update(
                str(pixmap.width).encode("utf-8")
            )

            h.update(
                str(pixmap.height).encode("utf-8")
            )

            # 실제 픽셀
            h.update(
                pixmap.samples
            )

        return h.hexdigest()

    except Exception as error:

        print()
        print("[ERROR] Failed to process PDF:")
        print(path)
        print(error)

        raise

    finally:

        if document is not None:
            document.close()


# =========================================================
# 날짜 폴더 snapshot
# =========================================================

def get_pdf_snapshot(date_dir):

    snapshot = {}

    pdf_paths = sorted(
        path
        for path in date_dir.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower() == ".pdf"
        )
    )

    for path in pdf_paths:

        relative_path = (
            path
            .relative_to(date_dir)
            .as_posix()
        )

        print(
            f"Hashing [{date_dir.name}] "
            f"{relative_path}"
        )

        snapshot[relative_path] = {
            "hash": visual_pdf_hash(path),
            "name": path.name,
        }

    return snapshot


# =========================================================
# Moved / Renamed 판정
#
# 매우 보수적으로 처리한다.
#
# 1순위
#   visual hash 같음
#   + 파일명 같음
#
# 2순위
#   visual hash 같음
#   + 같은 최상위 subject
#   + 파일명이 충분히 유사함
#
# hash만 같다는 이유로는 절대로 이동으로 처리하지 않는다.
#
# 따라서 예:
#
# Bounded Variation
# ->
# Dihedral Group
#
# 같은 잘못된 연결을 막는다.
# =========================================================

def detect_moves(
    previous,
    current,
    deleted_candidates,
    added_candidates
):

    moved = []


    # -----------------------------------------------------
    # hash별 후보
    # -----------------------------------------------------

    deleted_by_hash = defaultdict(list)

    for path in deleted_candidates:

        deleted_by_hash[
            previous[path]["hash"]
        ].append(path)


    added_by_hash = defaultdict(list)

    for path in added_candidates:

        added_by_hash[
            current[path]["hash"]
        ].append(path)


    common_hashes = (
        set(deleted_by_hash)
        & set(added_by_hash)
    )


    # =====================================================
    # STEP 1
    #
    # 동일 visual hash + 동일 파일명
    #
    # 가장 확실한 이동
    # =====================================================

    for file_hash in sorted(common_hashes):

        old_paths = sorted(
            path
            for path in deleted_by_hash[file_hash]
            if path in deleted_candidates
        )

        new_paths = sorted(
            path
            for path in added_by_hash[file_hash]
            if path in added_candidates
        )


        old_by_name = defaultdict(list)

        for old_path in old_paths:

            old_by_name[
                normalized_filename(old_path)
            ].append(old_path)


        new_by_name = defaultdict(list)

        for new_path in new_paths:

            new_by_name[
                normalized_filename(new_path)
            ].append(new_path)


        same_names = (
            set(old_by_name)
            & set(new_by_name)
        )


        for name in sorted(same_names):

            old_list = sorted(
                old_by_name[name]
            )

            new_list = sorted(
                new_by_name[name]
            )

            pair_count = min(
                len(old_list),
                len(new_list)
            )


            for index in range(pair_count):

                old_path = old_list[index]

                new_path = new_list[index]


                if (
                    old_path not in deleted_candidates
                    or new_path not in added_candidates
                ):
                    continue


                moved.append(
                    {
                        "from": old_path,
                        "to": new_path,
                    }
                )


                deleted_candidates.remove(
                    old_path
                )

                added_candidates.remove(
                    new_path
                )


    # =====================================================
    # STEP 2
    #
    # 이름이 변경된 경우
    #
    # 조건:
    #
    # - visual hash 동일
    # - 같은 최상위 subject
    # - 이름 similarity >= threshold
    #
    # =====================================================

    deleted_by_hash = defaultdict(list)

    for path in deleted_candidates:

        deleted_by_hash[
            previous[path]["hash"]
        ].append(path)


    added_by_hash = defaultdict(list)

    for path in added_candidates:

        added_by_hash[
            current[path]["hash"]
        ].append(path)


    common_hashes = (
        set(deleted_by_hash)
        & set(added_by_hash)
    )


    possible_pairs = []


    for file_hash in common_hashes:

        old_paths = deleted_by_hash[file_hash]

        new_paths = added_by_hash[file_hash]


        for old_path in old_paths:

            old_subject = top_subject(old_path)

            old_name = normalized_filename(
                old_path
            )


            for new_path in new_paths:

                new_subject = top_subject(
                    new_path
                )

                # 서로 다른 학문 분야까지
                # rename으로 추측하지 않는다.
                if old_subject != new_subject:
                    continue


                new_name = normalized_filename(
                    new_path
                )


                similarity = SequenceMatcher(
                    None,
                    old_name,
                    new_name
                ).ratio()


                if (
                    similarity
                    >= RENAME_SIMILARITY_THRESHOLD
                ):

                    possible_pairs.append(
                        (
                            similarity,
                            old_path,
                            new_path
                        )
                    )


    # similarity가 높은 것부터 greedy matching
    possible_pairs.sort(
        key=lambda item: (
            -item[0],
            item[1],
            item[2]
        )
    )


    used_old = set()

    used_new = set()


    for (
        similarity,
        old_path,
        new_path
    ) in possible_pairs:


        if old_path in used_old:
            continue

        if new_path in used_new:
            continue

        if old_path not in deleted_candidates:
            continue

        if new_path not in added_candidates:
            continue


        moved.append(
            {
                "from": old_path,
                "to": new_path,
            }
        )


        used_old.add(old_path)

        used_new.add(new_path)


        deleted_candidates.remove(
            old_path
        )

        added_candidates.remove(
            new_path
        )


    return moved


# =========================================================
# 날짜 폴더 수집
#
# YYMMDD 6자리 숫자 폴더만 사용
# =========================================================

date_dirs = sorted(

    [
        path
        for path in UNTEXED.iterdir()

        if (
            path.is_dir()
            and path.name.isdigit()
            and len(path.name) == 6
        )
    ],

    key=lambda path: path.name
)


if not date_dirs:

    print("No dated folders found.")

    raise SystemExit(0)


print()
print("Found versions:")
print()

for date_dir in date_dirs:

    print(
        f"  {date_dir.name}"
    )

print()


# =========================================================
# 전체 snapshot 생성
# =========================================================

snapshots = {}


for date_dir in date_dirs:

    print()
    print("=" * 70)
    print(
        f"Scanning {date_dir.name}"
    )
    print("=" * 70)
    print()


    snapshots[
        date_dir.name
    ] = get_pdf_snapshot(
        date_dir
    )


# =========================================================
# Record 생성
# =========================================================

records = {}


for index, date_dir in enumerate(date_dirs):

    date = date_dir.name

    current = snapshots[date]


    # =====================================================
    # 최초 날짜
    #
    # 이전 snapshot이 없으므로
    # "전부 Added"라고 하지 않는다.
    #
    # Baseline snapshot으로 취급.
    # =====================================================

    if index == 0:

        records[date] = {

            "baseline": True,

            "added": [],

            "modified": [],

            "moved_renamed": [],

            "deleted": [],
        }

        continue


    # =====================================================
    # 이전 snapshot
    # =====================================================

    previous_date = (
        date_dirs[index - 1].name
    )

    previous = snapshots[
        previous_date
    ]


    previous_paths = set(
        previous.keys()
    )

    current_paths = set(
        current.keys()
    )


    # =====================================================
    # 동일 경로
    # =====================================================

    common_paths = (
        previous_paths
        & current_paths
    )


    # =====================================================
    # Modified
    #
    # 경로 동일 + 실제 화면 hash 변경
    # =====================================================

    modified_raw = sorted(

        path

        for path in common_paths

        if (
            previous[path]["hash"]
            != current[path]["hash"]
        )
    )


    # =====================================================
    # Added / Removed 후보
    # =====================================================

    added_candidates = set(
        current_paths
        - previous_paths
    )

    deleted_candidates = set(
        previous_paths
        - current_paths
    )


    # =====================================================
    # Moved / Renamed 추출
    #
    # 이동으로 확인된 항목은
    # Added / Removed 후보에서 제거된다.
    # =====================================================

    moved_raw = detect_moves(

        previous,

        current,

        deleted_candidates,

        added_candidates
    )


    # =====================================================
    # 최종 Record
    # =====================================================

    added = [

        display_path(path)

        for path in sorted(
            added_candidates
        )
    ]


    modified = [

        display_path(path)

        for path in modified_raw
    ]


    deleted = [

        display_path(path)

        for path in sorted(
            deleted_candidates
        )
    ]


    moved_renamed = [

        {
            "from": display_path(
                item["from"]
            ),

            "to": display_path(
                item["to"]
            ),
        }

        for item in sorted(
            moved_raw,
            key=lambda item: (
                item["from"],
                item["to"]
            )
        )
    ]


    records[date] = {

        "baseline": False,

        "added": added,

        "modified": modified,

        "moved_renamed": moved_renamed,

        "deleted": deleted,
    }


# =========================================================
# YAML 저장
# =========================================================

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)


with OUTPUT.open(
    "w",
    encoding="utf-8"
) as file:

    yaml.safe_dump(

        records,

        file,

        allow_unicode=True,

        sort_keys=False,

        width=140,
    )


# =========================================================
# Summary
# =========================================================

print()
print("=" * 70)
print("Record summary")
print("=" * 70)
print()


for date, record in records.items():

    print(date)


    if record["baseline"]:

        print(
            "  Baseline snapshot"
        )

    else:

        print(
            f"  Added         : "
            f"{len(record['added'])}"
        )

        print(
            f"  Modified      : "
            f"{len(record['modified'])}"
        )

        print(
            f"  Moved/Renamed : "
            f"{len(record['moved_renamed'])}"
        )

        print(
            f"  Removed       : "
            f"{len(record['deleted'])}"
        )


    print()


print(
    f"Generated: {OUTPUT}"
)