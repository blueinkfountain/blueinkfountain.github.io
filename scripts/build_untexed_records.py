from pathlib import Path, PurePosixPath
from collections import defaultdict
import hashlib
import yaml
import fitz  # PyMuPDF


# =========================================================
# 경로 설정
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

UNTEXED = ROOT / "untexed"

OUTPUT = ROOT / "_data" / "untexed_records.yml"


# =========================================================
# Record에 표시할 경로
#
# 예:
# Algebra/1. Linear Algebra/Vector Space.pdf
#
# ->
#
# Algebra/1. Linear Algebra/Vector Space
# =========================================================

def display_path(relative_path):
    path = PurePosixPath(relative_path)

    return path.with_suffix("").as_posix()


# =========================================================
# PDF의 실제 "보이는 내용"을 Hash
#
# PDF 파일 자체의 binary hash가 아니라
# 각 페이지를 이미지로 렌더링한 결과를 비교한다.
#
# 따라서 다음은 Modified로 잡히지 않는다.
#
# - PDF 생성일 변경
# - 수정일 변경
# - Producer 변경
# - 내부 object 번호 변경
# - 압축 방식 변경
#
# 실제 페이지의 시각적 내용이 달라져야
# Modified로 판정된다.
# =========================================================

def visual_pdf_hash(path):
    h = hashlib.sha256()

    document = None

    try:
        document = fitz.open(path)

        # 페이지 수 자체도 비교 대상
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
            h.update(pixmap.samples)

        return h.hexdigest()

    except Exception as e:

        print()
        print(
            f"[ERROR] Failed to process PDF:"
        )

        print(path)

        print(e)

        raise

    finally:

        if document is not None:
            document.close()


# =========================================================
# 특정 날짜 폴더의 PDF snapshot
#
# 예:
#
# 260814/
#   Algebra/
#     1. Linear Algebra/
#       Vector Space.pdf
#
# snapshot key:
#
# Algebra/1. Linear Algebra/Vector Space.pdf
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
# 날짜 폴더 수집
#
# YYMMDD 형식의 6자리 숫자 폴더만 사용
#
# 예:
#
# 260807
# 260813
# 260814
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
    print(f"  {date_dir.name}")

print()


# =========================================================
# 모든 날짜 Snapshot 생성
# =========================================================

snapshots = {}


for date_dir in date_dirs:

    print()
    print("=" * 70)
    print(f"Scanning {date_dir.name}")
    print("=" * 70)
    print()

    snapshots[date_dir.name] = (
        get_pdf_snapshot(date_dir)
    )


# =========================================================
# 날짜별 Record 생성
# =========================================================

records = {}


for index, date_dir in enumerate(date_dirs):

    date = date_dir.name

    current = snapshots[date]


    # =====================================================
    # 최초 Snapshot
    #
    # 비교할 이전 버전이 없으므로
    # 전부 Added 처리
    # =====================================================

    if index == 0:

        records[date] = {

            "added": [
                display_path(path)
                for path in sorted(current.keys())
            ],

            "modified": [],

            "moved_renamed": [],

            "deleted": [],
        }

        continue


    # =====================================================
    # 이전 날짜
    # =====================================================

    previous_date = date_dirs[index - 1].name

    previous = snapshots[previous_date]


    previous_paths = set(previous.keys())

    current_paths = set(current.keys())


    # =====================================================
    # 1. 동일 경로끼리 먼저 비교
    # =====================================================

    common_paths = (
        previous_paths
        & current_paths
    )


    modified_raw = sorted(

        path

        for path in common_paths

        if (
            previous[path]["hash"]
            != current[path]["hash"]
        )
    )


    # =====================================================
    # 2. 일단 Added / Removed 후보 생성
    #
    # 아직 Moved/Renamed을 판별하기 전
    # =====================================================

    added_candidates = set(
        current_paths - previous_paths
    )

    deleted_candidates = set(
        previous_paths - current_paths
    )


    # =====================================================
    # 3. Removed 후보들을 visual hash별로 묶는다.
    #
    # hash:
    #   [old/path/A.pdf, old/path/B.pdf]
    # =====================================================

    deleted_by_hash = defaultdict(list)


    for old_path in sorted(deleted_candidates):

        file_hash = previous[old_path]["hash"]

        deleted_by_hash[file_hash].append(
            old_path
        )


    # =====================================================
    # 4. Added 후보들도 visual hash별로 묶는다.
    # =====================================================

    added_by_hash = defaultdict(list)


    for new_path in sorted(added_candidates):

        file_hash = current[new_path]["hash"]

        added_by_hash[file_hash].append(
            new_path
        )


    # =====================================================
    # 5. 동일한 visual hash인데 경로만 달라졌다면
    #
    # Moved / Renamed
    #
    # 로 판정
    #
    # 예:
    #
    # old:
    # Topology/General Topology/Product space.pdf
    #
    # new:
    # Topology/1. General Topology/Product space.pdf
    #
    # 내용 hash가 같으면
    #
    # Moved / Renamed
    # =====================================================

    moved_renamed_raw = []


    common_hashes = (
        set(deleted_by_hash.keys())
        & set(added_by_hash.keys())
    )


    for file_hash in sorted(common_hashes):

        old_paths = sorted(
            deleted_by_hash[file_hash]
        )

        new_paths = sorted(
            added_by_hash[file_hash]
        )


        # 동일 hash의 PDF가 여러 개 있을 수 있으므로
        # 정렬한 뒤 가능한 만큼 1:1 대응
        pair_count = min(
            len(old_paths),
            len(new_paths)
        )


        for i in range(pair_count):

            old_path = old_paths[i]

            new_path = new_paths[i]


            moved_renamed_raw.append({

                "from": old_path,

                "to": new_path,
            })


            # 이제 진짜 Added/Removed가 아니므로
            # 후보 목록에서 제거
            deleted_candidates.discard(
                old_path
            )

            added_candidates.discard(
                new_path
            )


    # =====================================================
    # 6. 최종 Added
    # =====================================================

    added = [

        display_path(path)

        for path in sorted(
            added_candidates
        )
    ]


    # =====================================================
    # 7. 최종 Modified
    # =====================================================

    modified = [

        display_path(path)

        for path in modified_raw
    ]


    # =====================================================
    # 8. 최종 Removed
    # =====================================================

    deleted = [

        display_path(path)

        for path in sorted(
            deleted_candidates
        )
    ]


    # =====================================================
    # 9. Moved / Renamed
    #
    # 여기에서도 .pdf 확장자를 제거한다.
    # =====================================================

    moved_renamed = [

        {
            "from": display_path(item["from"]),
            "to": display_path(item["to"]),
        }

        for item in sorted(
            moved_renamed_raw,
            key=lambda item: (
                item["from"],
                item["to"]
            )
        )
    ]


    records[date] = {

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
        width=120,
    )


# =========================================================
# 결과 Summary
# =========================================================

print()
print("=" * 70)
print("Record summary")
print("=" * 70)
print()


for date, record in records.items():

    print(date)

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